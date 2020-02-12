from infra import model
from infra.model import plugins
from automation_infra.plugins import connection
from automation_infra.plugins.ssh_direct import SshDirect


class SSH(SshDirect):
    TUNNEL_PORT = 2222

    def connect(self, port=TUNNEL_PORT, timeout=10):
        # TODO: have handle security here
        host = model.host.create_host(self._host.ip, 'root', 'pass', None)
        self._connection = connection.Connection(host, port)
        self._connection.connect(timeout)


plugins.register('SSH', SSH)
