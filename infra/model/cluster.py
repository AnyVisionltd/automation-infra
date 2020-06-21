from munch import Munch

from infra.model import plugins
from infra.model.host import Host
import copy

cluster_config_example = {
    "alias": "cluster1",
    "hosts": {
        "host1": {
            "ip": "192.168.20.34",
            "user": "user",
            "password": "pass",
            "key_file_path": "",
            "alias": "monster",
            "host_id": 123,
            "host_type": "virtual",
            "allocation_id": ""
        },
        "host2": {
            "ip": "192.168.20.75",
            "key_file_path": "/home/ori/.ssh/id_rsa",
            "user": "user",
            "password": "",
            "alias": "monster2",
            "host_type": "on-prem",
            "host_id": 123,
            "allocation_id": ""
        }
    }
}


class Cluster(object):

    def __init__(self, cluster_config_munch):
        # TODO: is this the type of thing you want??
        self.alias = cluster_config_munch.alias
        self.hosts = list()
        self.init_host_sshs(cluster_config_munch.hosts)

    def __str__(self):
        return self.alias

    def __getattr__(self, name):
        if name not in self.__plugins:
            # Access by key but if there's a problem raise an AttributeError to be consistent with expected behavior
            try:
                self.__plugins[name] = plugins.plugins[name](self)
            except KeyError:
                raise AttributeError
        return self.__plugins[name]

    def init_host_sshs(self, hosts_munch):
        for name, host_config in hosts_munch.items():
            config = copy.copy(host_config)
            config['alias'] = name
            host = Host(config)
            host.init_ssh()
            print(f"successfully initialized ssh for host: {host}")
            self.hosts.append(host)


plugins.register('Cluster', Cluster)


def test_functionality():
    print("Initializing cluster..")
    cluster = Cluster(Munch.fromDict(cluster_config_example))
    print("Successfully initialized cluster!")


if __name__ == '__main__':
    test_functionality()
