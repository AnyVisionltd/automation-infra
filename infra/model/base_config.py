import json
from munch import *

from infra.model import plugins
from infra.model.host import Host

example = {
        "alias": "config1",
        "cluster": {
            "alias": "cluster1",
            "hosts": {
                "host1": {
                    "ip": "192.168.20.34",
                    "user": "user",
                    "password": "password",
                    "key_file_path": "",
                    "alias": "monster",
                    "host_id": 123,
                    "host_type": "type1",
                    "allocation_id": ""
                }
            }
        },
        "streaming_server": {
            "uri": "rtmp://192.168.20.34/live/st1",
            "other_info": "more info here"
        }
    }


def nested_value(search_key, nested_dict):
    if search_key in nested_dict.keys():
        return nested_dict[search_key]

    for k, v in nested_dict.items():
        if isinstance(v, dict):
            res = nested_value(search_key, v)
            if res is not None:
                return res

    return None


class BaseConfig(DefaultMunch):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__plugins = {}

    def __str__(self):
        return self.alias

    def __getattr__(self, k):
        """ Gets key if it exists, otherwise checks if the key is one of the plugins (could me a model or a module)...
        If it is, inits the model/module, or otherwise returns the default value."""
        try:
            return Munch(self).__getattr__(k)
        except AttributeError:
            if k not in self.__plugins:
                # Access by key but if there's a problem raise an AttributeError to be consistent with expected behavior
                try:
                    self.__plugins[k] = plugins.plugins[k](self)
                except KeyError:
                    return self.__default__
            return self.__plugins[k]


def test_nested_values():
    with open("base_config.json", 'r') as f:
        j = json.load(f)
    assert nested_value("password", j) == 'password'
    assert nested_value("cluster", example) == {
        "alias": "cluster1",
        "hosts": {
            "host1": {
                "ip": "192.168.20.34",
                "user": "user",
                "password": "password",
                "key_file_path": "",
                "alias": "monster",
                "host_id": 123,
                "host_type": "type1",
                "allocation_id": ""
            }
        }
    }
    assert nested_value("foo", example) is None
    assert nested_value('host_id', example) == 123
    assert nested_value('allocation_id', example) == ""
    assert nested_value('uri', example) == "rtmp://192.168.20.34/live/st1"


def test_base_config_init():
    bc = BaseConfig.fromDict(example, DefaultFactoryMunch)
    assert bc.alias == 'config1'
    host = bc.cluster.hosts.host1.Host
    print("successful initializing (and connecting to) host")
    assert 1


if __name__ == '__main__':
    test_nested_values()
    test_base_config_init()
