import json
from automation_infra.utils import shell

def interfaces_ip_addresses():
    output = json.loads(shell.run_cmd("ip -4   -json a"))
    interfaces = {}
    for iface_info in output:
        iface_ips = [iface_addr['local'] for iface_addr in iface_info['addr_info']]
        interfaces[iface_info['ifname']] = iface_ips
    return interfaces


def docker_ip_address():
    return interfaces_ip_addresses()['docker0'][0]
