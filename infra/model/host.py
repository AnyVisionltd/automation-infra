import itertools
import logging
import random
import subprocess

from infra.model import plugins
import threading

from infra.utils import pem_key

EXAMPLE_IP = '35.231.0.137'

host_config_example1 = {
    "ip": EXAMPLE_IP,
    "user": "user",
    "password": "pass",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}

host_config_example2 = {
    "ip": EXAMPLE_IP,
    "user": "root",
    "key_file_path": "runner/docker_build/docker_user.pem",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}

host_config_example3 = {
    "ip": EXAMPLE_IP,
    "user": "root",
    "password": "pass",
}


class Host(object):

    def __init__(self, **host_config):
        _key = host_config.get('key_file_path', None) or host_config.get('pem_key_string', None)
        _pass = host_config.pop('password', None)
        assert (_pass and not _key) or (_key and not _pass), \
            "password and key are mutually exclusive (password=%s, key=%s)" % (_pass, _key)
        self.ip = host_config.pop('ip')
        if self.ip is None:
            raise ValueError("Host ip cannot be None")
        self.user = host_config.pop('user')
        self.alias = host_config.pop('alias', str(random.randint(0, 999)))
        self.port = host_config.pop('port', 22)
        self.tunnelport = host_config.pop('tunnelport', 2222)
        self.resource_manager_ep = host_config.pop('resource_manager_ep', None)
        self.vm_id = host_config.pop('vm_id', None)
        self.password = _pass
        pkey = host_config.pop('pem_key_string', None)
        self.pkey = pem_key.from_string(pkey) if pkey else None
        self.keyfile = host_config.pop('key_file_path', None)
        self.extra_config = host_config
        self.__plugins = {}
        self._temp_dir_counter = itertools.count()
        self._plugins_init_lock = threading.RLock()

    def _init_plugin_locked(self, name):
        if name in self.__plugins:
            return self.__plugins[name]
        try:
            self.__plugins[name] = plugins.plugins[name](self)
            return self.__plugins[name]
        except KeyError:
            logging.debug(f"plugin {name} wasnt found!")
            raise AttributeError

    def __getattr__(self, name):
        if name not in self.__plugins:
            with self._plugins_init_lock:
                self.__plugins[name] = self._init_plugin_locked(name)
                return self.__plugins[name]
        return self.__plugins[name]

    def mktemp(self, basedir=None, prefix=None, suffix=None):
        counter = self.unique()
        suffix = suffix or ""
        basedir = basedir or 'tmp'
        prefix = prefix or "_tmp_"
        return '/%(basedir)s/%(prefix)s%(counter)d%(suffix)s' % dict(basedir=basedir, prefix=prefix, counter=counter,
                                                                     suffix=suffix)

    def add_to_ssh_agent(self):
        pkey_str = pem_key.to_string(self.pkey)
        subprocess.run(["ssh-add", "-"], input=pkey_str.encode(),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def remove_plugin(self, name):
        if name in self.__plugins:
            self.__plugins.pop(name)

    def clear_plugins(self):
        for name, plugin in self.__plugins.items():
            if hasattr(plugin, "clear"):
                plugin.clear()
        if "SSH" in self.__plugins:
            self.SSH.disconnect()
        if "SshDirect" in self.__plugins:
            self.SshDirect.disconnect()
        self.__plugins.clear()

    def unique(self):
        return next(self._temp_dir_counter)

    def __str__(self):
        return self.ip

    @classmethod
    def from_args(cls, ip, user, password=None, key_file_path=None, pem_key_string=None, **kwargs):
        basic = {"ip": ip,
        "user": user,
        "password": password,
        "key_file_path": key_file_path,
        "pem_key_string": pem_key_string }
        basic.update(**kwargs)
        return cls(**basic)

plugins.register('Host', Host)


def test_functionality():
    host1 = Host(**host_config_example1)
    host2 = Host(**host_config_example2)
    host3 = Host(**host_config_example3)
    host4 = Host.from_args('0.0.0.0', 'user', 'pass')
    host5 = Host.from_args('0.0.0.0', 'user', key_file_path='/path/to/pem')
