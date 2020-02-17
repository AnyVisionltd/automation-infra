from infra.utils import shell
import logging
import netifaces
import ipaddress


def device_exists(device):
    try:
        shell.run_cmd("ip link show %s" % device, shell=True)
        return True
    except:
        return False


def delete_net_device(device):
    logging.info("Removing network device %s", device)
    shell.run_cmd("ip link del %s" % device, shell=True)


def add_macvlan_device(link_dev, macvlan_dev):
    logging.info("Add macvlan device %s to device %s", macvlan_dev, link_dev)
    shell.run_cmd(f"ip link add link {link_dev} {macvlan_dev} type macvlan mode bridge", shell=True)


def add_ip_to_device(device, ip_cidr):
    logging.info("Add ip address %s to device %s", ip_cidr, device)
    shell.run_cmd(f"ip address add {ip_cidr} dev {device}", shell=True)


def start_device(device):
    shell.run_cmd(f"ip link set dev {device} up", shell=True)


def add_route(network, device):
    logging.info("Add route %s device %s", network, device)
    shell.run_cmd(f"ip route add {network} dev {device}", shell=True)


def delete_routes(device):
    logging.info("Delete routes for device %s", device)
    shell.run_cmd(f"ip route flush dev {device}", shell=True)


def default_gateway(device_name):
    gateways = netifaces.gateways()[netifaces.AF_INET]
    return [gw for gw in gateways
                            if gw[1] == device_name and gw[2] == True][0]


def network_info(device_name):
    ip_infos = netifaces.ifaddresses(device_name)[netifaces.AF_INET]
    return [ipaddress.ip_interface("%s/%s" % (ip_info['addr'], ip_info['netmask']))
             for ip_info in ip_infos]


