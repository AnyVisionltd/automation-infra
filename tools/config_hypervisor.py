import subprocess
import yaml
import os
import random
import argparse
import json

def find_gpu_bus_addr():
    return subprocess.check_output("lspci -D | grep -i nvidia | grep -vi audio | awk '{print $1}'", 
                                    shell=True, 
                                    executable='/bin/bash')

def randomMAC(type="xen"):
    """Generate a random MAC address.
    00-16-3E allocated to xensource
    52-54-00 used by qemu/kvm
    The OUI list is available at http://standards.ieee.org/regauth/oui/oui.txt.
    The remaining 3 fields are random, with the first bit of the first
    random field set 0.
    >>> randomMAC().startswith("00:16:3E")
    True
    >>> randomMAC("foobar").startswith("00:16:3E")
    True
    >>> randomMAC("xen").startswith("00:16:3E")
    True
    >>> randomMAC("qemu").startswith("52:54:00")
    True
    @return: MAC address string
    """
    ouis = { 'xen': [ 0x00, 0x16, 0x3E ], 'qemu': [ 0x52, 0x54, 0x00 ] }

    try:
        oui = ouis[type]
    except KeyError:
        oui = ouis['xen']

    mac = oui + [
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def randomUUID():
    """Generate a random UUID."""

    return [ random.randint(0, 255) for dummy in range(0, 16) ]

def uuidToString(u):
    """ Example: print(f"UID: {uuidToString(randomUUID())}") """
    return "-".join(["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2,
                     "%02x" * 6]) % tuple(u)

def uuidFromString(s):
    s = s.replace('-', '')
    return [ int(s[i : i + 2], 16) for i in range(0, 32, 2) ]


if __name__ == '__main__':
    # add arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--max-vms', type=int, default=4, help="maximum VMs")
    args = parser.parse_args()

    hypervisor_config_dir = os.path.realpath(f'{os.path.split(__file__)[0]}/../config')
    hypervisor_config_file = 'hypervisor.yaml'
    hypervisor_config_path = f"{hypervisor_config_dir}/{hypervisor_config_file}"
    hypervisor_config = dict()

    # add nvidia pci device bus info (address) into hypervisor_config_path
    hypervisor_config['pcis'] = []
    for businfo in find_gpu_bus_addr().decode("utf-8").splitlines():
        hypervisor_config['pcis'].append({'pci': businfo})
    
    # generate macs
    hypervisor_config['macs'] = []
    for i in range(0, args.max_vms):
        hypervisor_config['macs'].append(randomMAC(type='qemu'))

    # generate hypervisor config yaml
    os.makedirs(hypervisor_config_dir, exist_ok=True)
    if not os.path.exists(hypervisor_config_path):
        with open(hypervisor_config_path, 'w') as yaml_file:
            yaml.dump(hypervisor_config, yaml_file, default_flow_style=False)