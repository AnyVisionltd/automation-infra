import subprocess
import re 
import logging


def local_nvidia():
    proc = subprocess.Popen(['sudo', 'lspci', '-D'], stdout=subprocess.PIPE)
    output = proc.communicate()[0].decode("utf-8").split("\n")
    return parse_nvidia_lspci_output(output)


LSPCI_D_REGEX = "(([0-9a-f]{4}):([0-9a-f]{2}):([0-9a-f]{2}).([0-9a-f]))\s"


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
            bus_function = re.match(LSPCI_D_REGEX, ignore_case_line)
            if not bus_function:
                logging.error("Unexpected output from pci device %s", line)
                continue
            pci_device_string = bus_function.groups()[0]
            domain = bus_function.groups()[1]
            bus = bus_function.groups()[2]
            device = bus_function.groups()[3]
            function = bus_function.groups()[4]
            info = device_info(pci_device_string)
            logging.debug("Found device %s in %s", pci_device_string, line)
            device = {"domain" : domain,
                      "bus" : bus,
                      "device" : device,
                      "function" : function,
                      "info" : info}
            nvidia_devices[pci_device_string] = device
    return nvidia_devices


if __name__ == '__main__':
    print(local_nvidia())
