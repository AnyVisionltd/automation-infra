import logging

from infra.model import forward, plugins


class Tunnel(object):
    def __init__(self, host):
        self._host = host
        self.tunnels = dict()

    def get_or_create(self, service_name, dns_name, port):
        return self.tunnels.get(service_name, default=self._create_tunnel(service_name, dns_name, port))

    def _create_tunnel(self, service_name, remote, port):
        forward_server, local_bind_port = self.start_tunnel(remote, port)
        # TODO: I think i dont need the forward_server for anything, but what exactly is a tunnel object?
        # for now just using a local_bind_port as the tunnel bc thats all I think we really need:
        self.tunnels[service_name] = local_bind_port
        return self.tunnels[service_name]

    def start_tunnel(self, remote, port):
        """This function opens a tunnel to remote:port by trying to bind the same local port to the remote but if
        that port is taken just does a random free local port"""
        try:
            forward_server, local_bind_port = forward.start_tunnel(
                remote, port, self._host.SSH.get_transport(), port)
        except OSError:
            # cant map tunnel to local with same port bc port is in use in local
            forward_server, local_bind_port = forward.start_tunnel(remote, port, self._host.SSH.get_transport())
        logging.info(f"local bind port: {local_bind_port}")
        return forward_server, local_bind_port


plugins.register("Tunnel", Tunnel)
