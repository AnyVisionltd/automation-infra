import logging
from lab import NotEnoughResourceException
import munch


class Allocator(object):

    def __init__(self, mac_addresses, gpus_list, vm_manager, server_name, max_vms,
                 sol_base_port, paravirt_device, private_network="default"):
        self.mac_addresses = mac_addresses
        self.gpus_list = gpus_list
        self.vms = {}
        self.vm_manager = vm_manager
        self.server_name = server_name
        self.max_vms = max_vms
        self.paravirt_net_device = paravirt_device
        self.private_network = private_network
        self.sol_base_port = sol_base_port

    def _sol_port(self):
        return self.sol_base_port + len(self.vms)

    def _reserve_gpus(self, num_gpus):
        gpus = self.gpus_list[:num_gpus]
        self.gpus_list = self.gpus_list[num_gpus:]
        return gpus

    def _reserve_macs(self, num_macs):
        required_macs = self.mac_addresses[:len(num_macs)]
        self.mac_addresses = self.mac_addresses[len(num_macs):]
        return required_macs

    def _reserve_networks(self, networks):
        required_macs = self._reserve_macs(networks)

        return [{"macaddress" : mac,
                 "mode" : network_type,
                 'source' : self.paravirt_net_device if network_type == 'bridge' else self.private_network}
                for mac, network_type in zip(required_macs, networks)]

    def _free_vm_resources(self, gpus, networks):
        macs = [net['macaddress'] for net in networks]
        self.gpus_list.extend(gpus)
        self.mac_addresses.extend(macs)

    @staticmethod
    def _validate_networks_params(networks):
        for net in networks:
            if net not in ('bridge', 'isolated'):
                raise ValueError(f"Invalid network parameter {networks}")

    async def allocate_vm(self, base_image, memory_gb, networks, num_gpus=0, num_cpus=4, disks=None):
        ''' 
        @networks - list of networks that we want to allocate, possible 
        values are "isolated, bridge"
        @num_gpus - number of GPU`s to allocate 
        @num_cpus - number of CPU`s to allocate
        @memory_gb - memory in GB for vm
        @disks   - dict of {"size" : X, 'type' : [ssd or hdd]} to allocate disks
        '''
        disks = disks or []
        logging.debug("Allocate vm image %(base_image)s memory %(memory_gb)s networks\
                       %(networks)s cpus %(num_cpus)s gpus %(num_gpus)s disks %(disks)s",
                      dict(base_image=base_image, memory_gb=memory_gb, num_gpus=num_gpus, num_cpus=num_cpus, networks=networks, disks=disks))

        # check that i have enough networks in pool 
        if len(networks) > len(self.mac_addresses):
            raise NotEnoughResourceException(f"Not nrough mac addresses in pool requested: {networks} has {self.mac_addresses}")
        # Check that i have enough gpus 
        if num_gpus > len(self.gpus_list):
            raise NotEnoughResourceException(f"Not enough gpus requested : {num_gpus} has {self.gpus_list}")

        Allocator._validate_networks_params(networks)

        if self.max_vms == len(self.vms):
            raise NotEnoughResourceException(f"Cannot allocate more vms currently {self.vms}")

        gpus = self._reserve_gpus(num_gpus)
        networks = self._reserve_networks(networks)
        vm_name = "%s-vm-%d" % (self.server_name, len(self.vms))
        vm = munch.Munch(name=vm_name, num_cpus=num_cpus, memsize=memory_gb,
                         net_ifaces=networks, sol_port=self._sol_port(),
                         pcis=gpus, base_image=base_image,
                         disks=disks)
        self.vms[vm_name] = vm

        try:
            await self.vm_manager.allocate_vm(vm)
        except:
            self._free_vm_resources(gpus, networks)
            del self.vms[vm_name]
            raise
        else:
            logging.info("Allocated vm {vm}")
        return vm

    async def destroy_vm(self, name):
        vm = self.vms[name]
        try:
            await self.vm_manager.destroy_vm(vm)
        except:
            logging.exception("Failed to free vm %s", vm['name'])
            raise
        else:
            del self.vms[name]
            self._free_vm_resources(vm.pcis, vm.net_ifaces)