import itertools

from munch import Munch

from infra.model import plugins
from infra.plugins.ssh import SSH

host_config_example1 = {
    "ip": "192.168.20.34",
    "user": "user",
    "password": "pass",
    "key_file_path": "",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}
host_config_example2 = {
    "ip": "192.168.20.75",
    "user": "user",
    "password": "",
    "key_file_path": "/home/ori/.ssh/id_rsa",
    "alias": "monster",
    "host_id": 123,
    "host_type": "on-prem",
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
        self.init_ssh()

    def __getattr__(self, name):
        if name not in self.__plugins:
            # Access by key but if there's a problem raise an AttributeError to be consistent with expected behavior
            try:
                self.__plugins[name] = plugins.plugins[name](self)
            except KeyError:
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

    def init_ssh(self):
        try:
            self.SSH.execute('ls /', timeout=5)
        except Exception as e:
            print(e)
            raise
        return


plugins.register('Host', Host)


def test_functionality():
    print("initializing host1...")
    host1 = Host(Munch.fromDict(host_config_example1))
    print(f"successful constructing {host1}")

    print("initializing host2...")
    host2 = Host(Munch.fromDict(host_config_example2))
    print(f"successful constructing {host2}")


if __name__ == '__main__':
    test_functionality()
