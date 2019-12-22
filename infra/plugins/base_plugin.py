from infra.model import forward


class TunneledPlugin(object):
    """ This constitutes a base class for a plugin which enables tunnelling communication through 
    hosts existing SSH connection.
    To use, implementer needs to call start_tunnel with remote and port, and then to
    address localhost:{self.local_bind_port}
    Stop_tunnel can be called at the end but isn't really necessary bc its running on a daemon thread which will close
    when app ends."""
    def __init__(self, host):
        self._host = host
        self._forward_server = None
        self.local_bind_port = None
        
    def start_tunnel(self, remote, port):
        self._forward_server, self.local_bind_port = forward.start_tunnel(remote, port, self._host.SSH.get_transport())

    def stop_tunnel(self):
        self._forward_server.shutdown()


# TODO: add functionality: reconnect (all plugins which obv were disconnected at once if one was disconnected) 
# is_connected property

##### EXAMPLE ##########
import requests
from runner import helpers
from infra.model import plugins


class ExamplePlugin(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'example.tls.ai' if not helpers.is_k8s(self._host.SSH) else 'example.default.svc.cluster.local'
        self.PORT = 1234

    def get_file(self, rel_path):
        self.start_tunnel(self.DNS_NAME, self.PORT)
        res = requests.get(f"http://localhost:{self.local_bind_port}/{rel_path}")
        return res


plugins.register('ExamplePlugin', ExamplePlugin)
