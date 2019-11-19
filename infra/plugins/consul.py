import sshtunnel
import consul
from munch import Munch

from runner import CONSTS
from infra.model import plugins


class Consul(object):
    def __init__(self, host=Munch(ip='0.0.0.0', user='user', password='user1!')):
        self._tunnel = sshtunnel.open_tunnel(host.ip,
                                             ssh_username=host.user, ssh_password=host.password, ssh_pkey=host.keyfile,
                                             remote_bind_address=(CONSTS.CONSUL, CONSTS.CONSUL_PORT))
        self._tunnel.start()
        self._consul = consul.Consul('localhost', self._tunnel.local_bind_port)

    def get_services(self):
        return self._consul.catalog.services()

    def put_key(self, key, val):
        res = self._consul.kv.put(key, val)
        return res

    def get_key(self, key):
        res = self._consul.kv.get(key)[1]['Value']
        return res


plugins.register('Consul', Consul)
