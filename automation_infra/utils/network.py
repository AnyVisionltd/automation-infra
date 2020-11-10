import json
from automation_infra.utils import shell


def parse_interfaces(data):
    interfaces = {}
    for iface_info in data:
        iface_ips = [iface_addr['local'] for iface_addr in iface_info['addr_info']]
        interfaces[iface_info['ifname']] = iface_ips
    return interfaces


def interfaces_ip_addresses():
    output = json.loads(shell.run_cmd("ip -4   -json a"))
    return parse_interfaces(output)


def docker_ip_address():
    return interfaces_ip_addresses()['docker0'][0]


def interfaces_ip_addresses_remote(host):
    output = json.loads(host.SshDirect.execute("ip -4   -json a"))
    return parse_interfaces(output)


def docker_ip_address_remote(host):
    return interfaces_ip_addresses_remote(host)['docker0'][0]
