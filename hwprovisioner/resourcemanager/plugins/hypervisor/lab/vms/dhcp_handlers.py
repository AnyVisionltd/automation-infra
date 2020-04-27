import scapy
from scapy import config as scapy_conf
from scapy import arch as scapy_arch
from scapy.layers import l2, inet, dhcp
from scapy import sendrecv
import codecs
import concurrent.futures
import asyncio
import logging
import threading
from infra.utils import waiter
# This conf is needed to make dhcp requests, so that responses
# will be not be checked against our real ip address
scapy_conf.conf.checkIPaddr = False


class DHCPRequestor(object):
    '''  The purpose of this class is to deal with sysadmins that does not
    give me access to dhcp server, and i need to guess VM ip in advance to return
    to the client what would be ip address of the vm after it will be created,
    so we take vm mac address and its name and send dhcp request.. nasty stuff
    '''

    def __init__(self, net_iface, loop, verbose=False, dhcp_timeout_sec=10):
        self._loop = loop
        self._net_iface = net_iface
        self._real_mac = scapy_arch.get_if_hwaddr(self._net_iface)
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self._dhcp_timeout_sec = dhcp_timeout_sec
        self._verbose = verbose

    @staticmethod
    def _dhcp_reply_info(dhcp_reply):
        bootp = dhcp_reply.getlayer('BOOTP')
        options_list = bootp.payload.getfieldval('options')
        result = {"ip" : bootp.yiaddr}
        for option in options_list:
            if type(option) is tuple:
                result[option[0]] = option[1]
        return result

    def _dhcp_request(self, mac_raw, requested_ip, xid_cookie=0, server_id="0.0.0.0", timeout_sec=10):
        logging.debug(f"Sending dhcp request for {requested_ip} cookie {xid_cookie} server id {server_id} net {self._net_iface}")
        dhcp_request = l2.Ether(src=self._real_mac, dst="ff:ff:ff:ff:ff:ff") / \
                        inet.IP(src="0.0.0.0", dst="255.255.255.255") / \
                        inet.UDP(sport=68, dport=67) / \
                        dhcp.BOOTP(chaddr=mac_raw, xid=xid_cookie) / \
                        dhcp.DHCP(options=[("message-type", "request"), ("server_id", server_id),
                                      ("requested_addr", requested_ip), ("param_req_list", 0), "end"])

        # send request, wait for ack
        dhcp_reply = sendrecv.srp1(dhcp_request, iface=self._net_iface, verbose=self._verbose, timeout=timeout_sec)
        if dhcp_reply is None:
            raise TimeoutError(f"DHCP request timeout on net {self._net_iface}")
        reply = DHCPRequestor._dhcp_reply_info(dhcp_reply)
        if dhcp.DHCPTypes[reply['message-type']] != 'ack':
            raise Exception("Failed to get ack %s" % reply)
        return reply

    def _do_request_lease(self, mac_address, ip=None, timeout_sec=10):
        logging.debug(f"Requesting lease for mac {mac_address} ip {ip} iface {self._net_iface}")
        mac_raw = codecs.decode(mac_address.replace(':', ''), 'hex')
        if ip is None:
            dhcp_discover = l2.Ether(src=self._real_mac, dst='ff:ff:ff:ff:ff:ff') / \
                            inet.IP(src='0.0.0.0', dst='255.255.255.255') / \
                            inet.UDP(dport=67, sport=68) / \
                            dhcp.BOOTP(chaddr=mac_raw, xid=scapy.volatile.RandInt()) / dhcp.DHCP(options=[('message-type', 'discover'), 'end'])
            dhcp_offer = sendrecv.srp1(dhcp_discover, iface=self._net_iface, verbose=self._verbose, timeout=timeout_sec)
            if dhcp_offer is None:
                raise TimeoutError(f"Timeout. failed to get offer for mac {mac_address} iface: {self._net_iface}")
            ip = dhcp_offer[dhcp.BOOTP].yiaddr
            server_id = dhcp_offer[dhcp.BOOTP].siaddr
            xid_cookie = dhcp_offer[dhcp.BOOTP].xid
        else:
            server_id = "0.0.0.0"
            xid_cookie = 0
        return self._dhcp_request(mac_raw, ip, xid_cookie, server_id, timeout_sec=timeout_sec)

    def _request_lease(self, mac_address, ip=None):
        dhcp_operation_timeout_sec = 3
        return waiter.wait_for_predicate_nothrow(lambda: self._do_request_lease(mac_address, ip=ip, timeout_sec=dhcp_operation_timeout_sec),
                                          timeout=self._dhcp_timeout_sec, exception_cls=TimeoutError)

    async def request_lease(self, mac, ip=None):
        lease_info = await self._loop.run_in_executor(self._thread_pool, lambda: self._request_lease(mac, ip))
        return lease_info['ip']

    async def release_lease(self, mac):
        pass


class LibvirtDHCPAllocator(object):

    def __init__(self, loop, libivrt_wrapper, network_name):
        self._libvirt = libivrt_wrapper
        self._net_name = network_name
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self._loop = loop
        self._ip_allocation_lock = threading.Lock()

    def _allocate_ip_sync(self, mac, ip=None):
        with self._ip_allocation_lock:
            dhcp_info = self._libvirt.get_network_dhcp_info(self._net_name)

            # Check if there are no free ips .. raise
            if len(dhcp_info['hosts']) == 0:
                raise Exception(f'IP range for network {self._net_name} is empty')

            # If we are with ip check that it is in the range
            if ip is not None:
                if ip not in dhcp_info['hosts']:
                    raise Exception(f"Requested ip {ip} not in dhcp range {dhcp_info['hosts']}")
                ip_candidate = ip
            else:
                ip_candidate = dhcp_info['hosts'].pop()

            logging.debug(f"Requesting least mac {mac} ip {ip_candidate}")
            self._libvirt.add_dhcp_entry(self._net_name, ip_candidate, mac)
        return str(ip_candidate)

    async def request_lease(self, mac, ip=None):
        lease_info = await self._loop.run_in_executor(self._thread_pool, lambda: self._allocate_ip_sync(mac, ip))
        return lease_info

    async def release_lease(self, mac):
        await self._loop.run_in_executor(self._thread_pool, lambda: self._libvirt.remove_dhcp_entry(self._net_name, mac))


class DHCPManager(object):

    def __init__(self, handlers):
        self._handlers = handlers

    async def allocate_ip(self, net_info):
        net_type = net_info['mode']
        logging.debug(f"Allocating ip for net {net_info}")
        mac = net_info['macaddress']
        ip = net_info.get('ip', None)
        return await self._handlers[net_type].request_lease(mac, ip)

    async def deallocate_ip(self, net_info):
        net_type = net_info['mode']
        logging.debug(f"Releasig lease for net {net_info}")
        mac = net_info['macaddress']
        return await self._handlers[net_type].release_lease(mac)

    async def reallocate_ip(self, net_info):
        logging.debug(f"Reallocate ip net {net_info}")
        try:
            await self.deallocate_ip(net_info)
        except:
            # we dont care if deallocate ip had failed we just do it to make sure it is released
            pass
        await self.allocate_ip(net_info)


if __name__ == '__main__':
    import argparse
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    parser = argparse.ArgumentParser()
    parser.add_argument("--iface", help="Name of the interface")
    parser.add_argument("--ip", help="IP to ask", required=False, default=None)
    parser.add_argument("mac", help="Mac address to request")

    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    client = DHCPRequestor(args.iface, loop)
    print(loop.run_until_complete(client.request_lease(args.mac, args.ip)))
