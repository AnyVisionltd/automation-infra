from . import plugins
import itertools


class Host(object):

    def __init__(self, host_config):
        assert (host_config.password and not host_config.key_file_path) or (not host_config.password and host_config.key_file_path), \
            "password and key are mutually exclusive (password=%s, key=%s)" % (host_config.password, host_config.key_file_path)

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
                raise AttributeError
        return self.__plugins[name]

    def mktemp(self, basedir=None, prefix=None, suffix=None):
        counter = self.unique()
        suffix = suffix or ""
        basedir = basedir or '/tmp'
        prefix = prefix or "_tmp_"
        return '/%(basedir)s/%(prefix)s%(counter)d%(suffix)s' % dict(basedir=basedir, prefix=prefix, counter=counter, suffix=suffix)

    def unique(self):
        return next(self._temp_dir_counter)

    def __str__(self):
        return self.alias


plugins.register('Host', Host)
