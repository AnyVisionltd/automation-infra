import itertools

from munch import Munch

from infra.model import plugins

EXAMPLE_IP = '35.231.0.137'

host_config_example1 = {
    "ip": EXAMPLE_IP,
    "user": "user",
    "password": "pass",
    "key_file_path": "",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}

host_config_example2 = {
    "ip": EXAMPLE_IP,
    "user": "root",
    "password": "",
    "key_file_path": "runner/docker_build/docker_user.pem",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}


class Host(object):

    def __init__(self, host_config):
        assert (host_config.password and not host_config.key_file_path) or (
                    not host_config.password and host_config.key_file_path), \
            "password and key are mutually exclusive (password=%s, key=%s)" % (
            host_config.password, host_config.key_file_path)
        self.ip = host_config.ip
        self.user = host_config.user
        self.alias = host_config.alias
        self.password = host_config.password
        self.keyfile = host_config.key_file_path
        self.id = host_config.host_id
        self.type = host_config.host_type
        self.allocation_id = host_config.allocation_id
        self.__plugins = {}
        self._temp_dir_counter = itertools.count()

    def __getattr__(self, name):
        if name not in self.__plugins:
            # Access by key but if there's a problem raise an AttributeError to be consistent with expected behavior
            try:
                self.__plugins[name] = plugins.plugins[name](self)
            except KeyError:
                print(f"plugin {name} wasnt found!")
                raise AttributeError
        return self.__plugins[name]

    def mktemp(self, basedir=None, prefix=None, suffix=None):
        counter = self.unique()
        suffix = suffix or ""
        basedir = basedir or '/tmp'
        prefix = prefix or "_tmp_"
        return '/%(basedir)s/%(prefix)s%(counter)d%(suffix)s' % dict(basedir=basedir, prefix=prefix, counter=counter,
                                                                     suffix=suffix)

    def unique(self):
        return next(self._temp_dir_counter)

    def __str__(self):
        return self.ip


plugins.register('Host', Host)


def create_host(ip, u, p=None, pem_path=None):
    host_config = {
        "ip": ip,
        "user": u,
        "password": p,
        "key_file_path": pem_path,
        "alias": "monster",
        "host_id": 123,
        "host_type": "virtual",
        "allocation_id": ""
    }
    host = Host(Munch.fromDict(host_config))
    return host


def test_functionality():
    print("initializing host1...")
    host1 = Host(Munch.fromDict(host_config_example1))
    print(f"successful constructing {host1}")


def init_example_hosts():
    host1 = Host(Munch.fromDict(host_config_example1))
    host2 = Host(Munch.fromDict(host_config_example2))
    return [host1, host2]


if __name__ == '__main__':
    test_functionality()
