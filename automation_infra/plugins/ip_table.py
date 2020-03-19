import subprocess
import os

from infra.model import plugins



class Iptables(object):

    IP_CHANGE_CMD = 'iptables -{action} DOCKER-USER --dst {service_name} -j REJECT'
    IP_FLUSH_CMD = 'iptables -t filter  --flush DOCKER-USER'
    IP_BLOCK_FORWARD_CMD = 'iptables -{action} FORWARD --dest {service_name} -j DROP'

    def __init__(self, host):
        self._host = host

    def __del__(self):
        self.flush()

    def flush(self):
        try:
            self._host.SSH.execute(self.IP_FLUSH_CMD)
        finally:
            return

    def block(self, service_name):
        self._host.SSH.execute(self.IP_CHANGE_CMD.format(action='I', service_name=service_name))

    def unblock(self, service_name):
        self._host.SSH.execute(self.IP_CHANGE_CMD.format(action='D', service_name=service_name))

    def block_forward(self, service_name):
        self._host.SSH.execute(self.IP_BLOCK_FORWARD_CMD.format(action='I', service_name=service_name))

    def unblock_forward(self, service_name):
        self._host.SSH.execute(self.IP_BLOCK_FORWARD_CMD.format(action='D', service_name=service_name))


plugins.register('Iptables', Iptables)
