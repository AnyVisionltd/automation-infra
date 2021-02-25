import threading

from munch import Munch

from infra.model import cluster_plugins
from infra.model.host import Host
import copy

cluster_config_example = {
    "cluster1": {
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
}

cluster_config_example2 = {'cluster1': {'hosts': ['host1']}}


class Cluster(object):

    def __init__(self, hosts_dict):
        self.hosts = Munch.fromDict(hosts_dict)
        self.__plugins = {}
        self._plugins_init_lock = threading.RLock()

    def __str__(self):
        return self.alias

    def __getattr__(self, name):
        if name not in self.__plugins:
            with self._plugins_init_lock:
                self.__plugins[name] = self._init_plugin_locked(name)
                return self.__plugins[name]
        return self.__plugins[name]

    def _init_plugin_locked(self, name):
        if name in self.__plugins:
            return self.__plugins[name]
        try:
            self.__plugins[name] = cluster_plugins.plugins[name](self)
            return self.__plugins[name]
        except KeyError:
            print(f"plugin {name} wasnt found!")
            raise AttributeError

    def init_host_sshs(self, hosts_munch):
        for name, host_config in hosts_munch.items():
            config = copy.copy(host_config)
            config['alias'] = name
            host = Host(config)
            host.init_ssh()
            print(f"successfully initialized ssh for host: {host}")
            self.hosts.append(host)

    def clear_plugins(self):
        self.__plugins.clear()
