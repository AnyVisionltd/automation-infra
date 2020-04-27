from infra.model import plugins
from infra.model.tunnel import Tunnel


class TunnelManager(object):
    def __init__(self, host):
        self._host = host
        self.tunnels = dict()

    def get_or_create(self, service_name, dns_name, port, transport=None):
        if service_name not in self.tunnels:
            self._init_tunnel(service_name, dns_name, port, transport)
        return self.tunnels[service_name]

    def stop(self, service_name):
        tunnel = self.tunnels.pop(service_name, default=None)
        if tunnel is not None:
            try:
                self._safe_stop_tunnel()
                tunnel.stop()
            except:
                pass

    def _init_tunnel(self, service_name, remote, port, transport):
        transport = transport if transport is not None else self._host.SSH.get_transport()
        tunnel = Tunnel(remote, port, transport)
        tunnel.start()
        self.tunnels[service_name] = tunnel

    def clear(self):
        for service_name in self.tunnels:
            self.stop(service_name)


plugins.register("TunnelManager", TunnelManager)
