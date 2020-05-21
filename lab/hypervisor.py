from os import path

from infra.utils import shell
from infra.utils import pci
from infra.utils import anylogging
import logging
from lab.vms import rest, cloud_init
from lab.vms import allocator
from lab.vms import vm_manager
from lab.vms import dhcp_handlers
from lab.vms import libvirt_wrapper
from lab.vms import image_store
from lab.vms import storage as libstorage
import asyncio
from aiohttp import web
import argparse
import yaml
from lab.utils import net


def _verify_gpu_drivers_not_loaded():
    nvidia_modules = shell.run_cmd("lsmod | grep nvidia")
    nouveau_modules = shell.run_cmd("lsmod | grep nouveau")
    if nvidia_modules or nouveau_modules:
        raise("Graphical kernel modules loaded nvidia: %s nouveau:\
        %s hypervisors cannot work with loaded modules", nvidia_modules, nouveau_modules)


def _check_kvm_ok():
    try:
        shell.run_cmd("kvm-ok")
    except:
        logging.error("KVM cannot run in accelerated mode are KVM modules exist?")
        raise


def _check_network_interface_up(net_iface):
    network_state = f"/sys/class/net/{net_iface}/operstate"
    with open(network_state, 'r') as f:
        net_state = f.read().strip()
    if net_state != "up":
        raise Exception(f"Network infterface {net_iface} is not operational")


def _check_libvirt_network_is_up(vmm, net_name):
    logging.info(f"Going to active network {net_name}")
    try:
        vmm.activate_network(net_name)
    except Exception as e:
        raise Exception("Network %s is not operational" % net_name) from e


def load_config(file_name):
    config = {}
    with open(file_name, 'r') as f:
        config_yaml = yaml.load(f.read())
    if config_yaml.get('pcis', None) is not None:
        config['pci'] = [pci.Device.from_full_address(pci_conf['pci'])
                         for pci_conf in config_yaml['pcis']]
    else:
        config['pci'] = []
    config['macs'] = config_yaml['macs']
    return config


MACVLAN_DEV_NAME = "vm-macvlan"


def _setup_macvlan_device(paravirt_device):
    # delete macvlan device if it exists and recreate
    if net.device_exists(MACVLAN_DEV_NAME):
        logging.info("Delete existing macvlan device")
        net.delete_routes(MACVLAN_DEV_NAME)
        net.delete_net_device(MACVLAN_DEV_NAME)
    ip_info = net.network_info(paravirt_device)
    logging.info("Device %s info %s", paravirt_device, ip_info)
    # in case we have several ip addresses .. lets take the first one
    net.setup_macvlan_device(paravirt_device, ip_info[0], MACVLAN_DEV_NAME)
    logging.info("Macvlan device %s is setup", MACVLAN_DEV_NAME)


def _vfio_bind_pci_devices(devices):
    logging.debug("Going to vfio bind devices %s", devices)
    for device in devices:
        # If device is already VFIO and it is in use we wont be able to bind it,
        # but we assume it is in-use by our VM`s and we are just reloading

        drvpath = f"/sys/bus/pci/devices/{device.domain}:{device.bus}:{device.slot}.{device.function}/driver"
        if not path.exists(drvpath):
            logging.error("%s does not exist! skipping VFIO bind", drvpath)
            continue

        if pci.device_driver(device) == 'vfio-pci' and pci.enable_count(device) > 0:
            logging.info("Skip binding device %s it is already vfio-pci and in-use", device)
            continue
        try:
            pci.vfio_bind_pci_device(device)
        except Exception as e:
            raise Exception("Failed to bind device %s verify", device) from e


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Config file containing pci addresses and mac addressses", required=True)
    parser.add_argument("--qemu-uri", help="qemu uri", default="qemu:///system")
    parser.add_argument("--images-dir", help="Default backing images dir", default="var/lib/libvirt/images")
    parser.add_argument("--run-dir", help="Images run dir", default="var/lib/libvirt/images")
    parser.add_argument("--ssd-dir", help="SSD disks dir, where ssd images will be stored", default="var/lib/libvirt/images")
    parser.add_argument("--hdd-dir", help="HDD disks dir, where hdd images will be stored", default="var/lib/libvirt/images")
    parser.add_argument("--log-level", help="Log level defaults to INFO", default="INFO")
    parser.add_argument("--max-vms", help="Maximum amount of VMs to support concurrently", default=1, type=int)
    parser.add_argument("--private-net", help="Private network device for NAT networks", default="default")
    parser.add_argument("--paravirt-net-device", help="Paravirtualized network device for bridge networks", required=True)
    parser.add_argument("--sol-port", help="Base port for Serial over lan", required=True, type=int)
    parser.add_argument("--server-name", help="Name of the server, this will be used in name of VM`s", required=True)
    parser.add_argument("--port", help="HTTP port of hypervisor server", default=8080, type=int)
    parser.add_argument("--restore-vms", dest='vms_restore', help="Restore VM`s previosly allocated", action="store_true", required=False)
    parser.add_argument("--delete-vms", dest='vms_restore', help="Delete VM`s previosly allocated", action="store_false", required=False)
    parser.set_defaults(vms_restore=True)

    args = parser.parse_args()
    log_level = logging.getLevelName(args.log_level)

    config = load_config(args.config)
    anylogging.configure_logging(root_level=log_level, console_level=log_level)
    loop = asyncio.get_event_loop()
    _check_kvm_ok()
    _setup_macvlan_device(args.paravirt_net_device)
    vmm = libvirt_wrapper.LibvirtWrapper(args.qemu_uri)
    _check_network_interface_up(args.paravirt_net_device)
    _check_libvirt_network_is_up(vmm, args.private_net)
    storage = image_store.ImageStore(loop, base_qcow_path=args.images_dir,
                                     run_qcow_path=args.run_dir,ssd_path=args.ssd_dir, hdd_path=args.hdd_dir)
    gpu_pci_devices = config['pci']
    _vfio_bind_pci_devices(config['pci'])
    ndb_driver = libstorage.NBDProvisioner()
    ndb_driver.initialize()
    vm_boot_init = cloud_init.CloudInit(args.run_dir)
    bridged_dhcp = dhcp_handlers.DHCPRequestor(args.paravirt_net_device, loop)
    nat_dhcp = dhcp_handlers.LibvirtDHCPAllocator(loop, vmm, args.private_net)
    dhcp_client = dhcp_handlers.DHCPManager(handlers={'bridge': bridged_dhcp, 'isolated' : nat_dhcp})
    manager = vm_manager.VMManager(loop, vmm, storage, ndb_driver, vm_boot_init, dhcp_client)
    allocator = allocator.Allocator(mac_addresses=config['macs'], gpus_list=gpu_pci_devices, vm_manager=manager,
                                    server_name=args.server_name, max_vms=args.max_vms, private_network=args.private_net,
                                    paravirt_device=args.paravirt_net_device, sol_base_port=args.sol_port)
    if args.vms_restore:
        loop.run_until_complete(allocator.restore_vms())
    else:
        loop.run_until_complete(allocator.delete_all_dangling_vms())
    app = web.Application()
    rest.HyperVisor(allocator, storage, app)
    web.run_app(app, port=args.port, access_log_format='%a %t "%r" time %Tf sec %s')
