import os
import sys

import yaml


def write_hw_yaml(path, hosts_dict):
    with open(path, 'w') as f:
        yaml.dump(hosts_dict, f)


if __name__ == '__main__':
    path = sys.argv[1]
    ips = sys.argv[2].split(',')
    ids = sys.argv[3].split(',')
    rm_ep = sys.argv[4]
    assert len(ips) == len(ids)
    hosts = dict()
    for i in range(len(ips)):
        hosts[f'host{i}'] = {'ip': ips[i], 'user': 'root', 'password': 'root',
                             'resource_manager_ep': rm_ep,
                             'vm_id': ids[i]}
    write_hw_yaml(path, hosts)
