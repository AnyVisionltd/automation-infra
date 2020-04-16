import libvirt
import logging
from . import vm_template
from contextlib import contextmanager
from libvirt import libvirtError
import xmltodict
import munch
import ipaddress
import netaddr


class LibvirtWrapper(object):

    def __init__(self, connection_uri):
        self.connection_uri = connection_uri

    @contextmanager
    def _libvirt_connection(self):
        connection = None
        try:
            connection = libvirt.open(self.connection_uri)
            yield connection
        except Exception as e:
            logging.exception("Libvirt operation failed")
            raise e
        finally:
            if connection is not None:
                connection.close()

    def _machine_metadata_xml(self, vm):
        data = vm.json
        data.update({'@xmlns:vm' : 'anyvision'})
        # wrap with namespace
        vm_instance = {'vm:instance' : data}
        return xmltodict.unparse(vm_instance, full_document=False)

    def _machine_metadata_xml_to_metadata(self, xml):
        vm_data = xmltodict.parse(xml, dict_constructor=dict, force_list=('net_ifaces', 'pcis', 'disks'))
        return munch.Munch(vm_data['instance'])

    def define_vm(self, machine_info):
        with self._libvirt_connection() as connection:
            xml = vm_template.generate_xml(machine_info, self._machine_metadata_xml(machine_info))
            logging.info("Defined vm %(name)s, xml: \n %(xml)s", dict(name=machine_info.name, xml=xml))
            connection.defineXML(xml)

    def start_vm(self, machine_info):
        name = machine_info.name
        with self._libvirt_connection() as connection:
            vm = connection.lookupByName(name)
            vm.create()
        logging.info("started vm %s", name)

    def poweroff_vm(self, machine_info):
        name = machine_info.name
        with self._libvirt_connection() as connection:
            vm = connection.lookupByName(name)
            vm.destroy()
        logging.info("VM %s destroyed", name)

    def status(self, name):
        libvirt_state_to_state = {libvirt.VIR_DOMAIN_NOSTATE  : "unknown",
                                  libvirt.VIR_DOMAIN_RUNNING  : "on",
                                  libvirt.VIR_DOMAIN_BLOCKED  : "fail",
                                  libvirt.VIR_DOMAIN_PAUSED   : "on",
                                  libvirt.VIR_DOMAIN_SHUTDOWN : "off",
                                  libvirt.VIR_DOMAIN_SHUTOFF  : "off",
                                  libvirt.VIR_DOMAIN_CRASHED  : "fail",
                                  libvirt.VIR_DOMAIN_PMSUSPENDED : "on"}
        with self._libvirt_connection() as connection:
            vm = connection.lookupByName(name)
            state = vm.state()[0]
            logging.info("VM state is %s - %s", state, libvirt_state_to_state[state])
            return libvirt_state_to_state[state]

    def kill_by_name(self, name):
        logging.debug("killimg vm %s", name)
        with self._libvirt_connection() as connection:
            try:
                vm = connection.lookupByName(name)
            except libvirt.libvirtError:
                logging.warning("VM %s is not found", name)
                return
            if vm.isActive():
                logging.info("vm is active")
                vm.destroy()
            vm.undefine()

    def dhcp_lease_info(self, name):
        '''
        @return:  network information from dhcp server for the VM, note that this will only
        work for isolated networks. DHCP information for other networks must be obtained
        from global dhcp server
        '''
        result = {}
        with self._libvirt_connection() as connection:
            vm = connection.lookupByName(name)
            nets = vm.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0)
        logging.debug("network info for vm %s is %s", name, nets)
        for net_info in nets.values():
            result[net_info['hwaddr']] = [net['addr'] for net in net_info['addrs']]
        return result

    def load_lab_vms(self):
        vms = []
        with self._libvirt_connection() as connection:
            domains = connection.listAllDomains()
            for domain in domains:
                try:
                    vm_xml = domain.metadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT, "anyvision")
                except libvirtError:
                    logging.info("Domain %s is not anyvision vm..skipping", domain.name())
                else:
                    data = self._machine_metadata_xml_to_metadata(vm_xml)
                    logging.debug("Loaded json %s for vm %s", data, domain.name())
                    vms.append(data)
        logging.info("Loaded %s", vms)
        return vms

    def add_dhcp_entry(self, network_name, ip, mac):
        logging.info(f"Adding dhcp entry to libvirt {network_name} {ip} {mac}")
        with self._libvirt_connection() as connection:
            net = connection.networkLookupByName(network_name)
            section = libvirt.VIR_NETWORK_SECTION_IP_DHCP_HOST
            xml = "<host mac='%s' ip='%s'/>" % (mac, ip)
            flags = (libvirt.VIR_NETWORK_UPDATE_AFFECT_LIVE |
                     libvirt.VIR_NETWORK_UPDATE_AFFECT_CONFIG)
            # first lets try add last command since in most cases this will be a new mac/ip
            # if that fails lets try update command (yes libvirt API sucks)
            try:
                net.update(libvirt.VIR_NETWORK_UPDATE_COMMAND_ADD_LAST, section, -1, xml, flags)
            except libvirtError:
                net.update(libvirt.VIR_NETWORK_UPDATE_COMMAND_MODIFY, section, -1, xml, flags)


    def remove_dhcp_entry(self, network_name, mac):
        logging.info(f"Remove dhcp entry to libvirt {network_name} {mac}")
        with self._libvirt_connection() as connection:
            net = connection.networkLookupByName(network_name)
            cmd = libvirt.VIR_NETWORK_UPDATE_COMMAND_DELETE
            section = libvirt.VIR_NETWORK_SECTION_IP_DHCP_HOST
            xml = "<host mac='%s'/>" % (mac)
            flags = (libvirt.VIR_NETWORK_UPDATE_AFFECT_LIVE |
                     libvirt.VIR_NETWORK_UPDATE_AFFECT_CONFIG)
            net.update(cmd, section, -1, xml, flags)

    def _network_info(self, network_name):
        with self._libvirt_connection() as connection:
            net = connection.networkLookupByName(network_name)
            net_info_xml = net.XMLDesc()
        return xmltodict.parse(net_info_xml, dict_constructor=dict, force_list=('host'))

    def get_network_dhcp_info(self, network_name):
        net_info = self._network_info(network_name)
        ipnet_info = net_info['network']['ip']
        ipnet = ipaddress.IPv4Network('%s/%s' % (ipnet_info['@address'], ipnet_info['@netmask']), strict=False)
        dhcp_range = ipnet_info['dhcp']['range']
        reserved_hosts = ipnet_info['dhcp'].get('host',[])
        permitted_range = netaddr.IPSet(netaddr.IPRange(dhcp_range['@start'], dhcp_range['@end']))
        # lets remove already reserved hosts from the list of allowed
        for dhcp_entry in reserved_hosts:
            permitted_range.remove(dhcp_entry['@ip'])

        reserved = [{'ip' : reserved_host['@ip'], 'mac': reserved_host['@mac']} for reserved_host in reserved_hosts]

        return {'net' : ipnet, 'hosts' : [ str(ip) for ip in permitted_range], 'reserved' : reserved}

