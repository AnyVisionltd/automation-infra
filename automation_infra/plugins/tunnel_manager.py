from infra.model import plugins
from infra.model.tunnel import Tunnel
import logging
from automation_infra.utils import concurrently


class TunnelManager(object):
    def __init__(self, host):
        self._host = host
        self.tunnels = dict()

    def get_or_create(self, service_name, dns_name, port, transport=None):
        if service_name not in self.tunnels:
            self._init_tunnel(service_name, dns_name, port, transport)
        return self.tunnels[service_name]

    def _do_stop(self, tunnel):
        try:
            tunnel.stop()
        except:
            logging.warning(f"Failed to stop tunnel {tunnel}", exc_info=True)

    def stop(self, service_name):
        tunnel = self.tunnels.pop(service_name, None)
        if tunnel is None:
            return
        self._do_stop(tunnel)

    def _init_tunnel(self, service_name, remote, port, transport):
        transport = transport if transport is not None else self._host.SSH.get_transport()
        tunnel = Tunnel(remote, port, transport)
        tunnel.start()
        self.tunnels[service_name] = tunnel

    def clear(self):
        if not self.tunnels:
            return
        concurrently.run([lambda: self._do_stop(tunnel) for tunnel in self.tunnels.values()])
        self.tunnels.clear()


plugins.register("TunnelManager", TunnelManager)
