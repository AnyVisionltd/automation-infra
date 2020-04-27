import subprocess
import re 
import logging
import munch
from infra.utils import shell
from builtins import staticmethod
import os

LSPCI_D_REGEX = re.compile("(([0-9a-f]{4}):([0-9a-f]{2}):([0-9a-f]{2}).([0-9a-f]))\s*")


class Device(munch.Munch):

    def __init__(self, domain, bus, slot, function, info):
        super().__init__(dict(domain=domain,
                               bus=bus,
                               slot=slot,
                               function=function,
                               info=info))

    @staticmethod
    def from_full_address(address):
        match = LSPCI_D_REGEX.match(address)
        if match is None:
            raise Exception("Address %s is not a pci address" % address)
        pci_info = match.groups()
        info = device_info(address)
        return Device(pci_info[1], pci_info[2], pci_info[3], pci_info[4],info=info)

    @property
    def full_address(self):
        return "%s:%s:%s.%s" % (self.domain, self.bus, self.slot, self.function)


def local_nvidia():
    output = shell.run_cmd("sudo lspci -D").split('\n')
    logging.debug("parsing lspci %s", output)
    return parse_nvidia_lspci_output(output)


def device_info(pci_address):
    info = {}
    info_files = ("current_link_speed", "max_link_speed", "max_link_width",
                  "current_link_width", "local_cpulist")
    for info_name in info_files:
        with open("/sys/bus/pci/devices/%s/%s" % (pci_address, info_name)) as f:
            info[info_name] = f.read().strip()
    return info


def parse_nvidia_lspci_output(lspci_output):
    nvidia_devices = {}
    for line in lspci_output: 
        ignore_case_line = line.lower()
        # check if this is an nvidia device but not sound device
        if "nvidia" in ignore_case_line and "audio" not in ignore_case_line:
            bus_function = LSPCI_D_REGEX.match(ignore_case_line)
            if not bus_function:
                logging.error("Unexpected output from pci device %s", line)
                continue
            pci_device_string = bus_function.groups()[0]
            domain = bus_function.groups()[1]
            bus = bus_function.groups()[2]
            slot = bus_function.groups()[3]
            function = bus_function.groups()[4]
            info = device_info(pci_device_string)
            logging.debug("Found device %s in %s", pci_device_string, line)
            device = Device(domain=domain,
                               bus=bus,
                               slot=slot,
                               function=function,
                               info=info)
            nvidia_devices[pci_device_string] = device
    return nvidia_devices


def vfio_bind_pci_device(device):
    logging.debug("vfio bind device %s", device)
    shell.run_cmd(["/usr/local/bin/vfio-pci-bind.sh", device.full_address])

def device_driver(device):
    path = f'/sys/bus/pci/devices/{device.full_address}/driver'
    driver_path = os.readlink(path)
    return driver_path.split('/')[-1]

def enable_count(device):
    path = f'/sys/bus/pci/devices/{device.full_address}/enable'
    with open(path, 'r') as f:
        return int(f.read().strip())

def vfio_bind_pci_devices(devices):
    logging.debug("Going to vfio bind devices %s", devices)
    for device in devices:
        vfio_bind_pci_device(device)


if __name__ == '__main__':
    print(local_nvidia())
