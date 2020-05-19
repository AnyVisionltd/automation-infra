import logging
import select
import threading

from automation_infra.utils import waiter

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer




class Tunnel(object):
    def __init__(self, dns_name, port, transport):
        self.remote_dns_name = dns_name
        self.remote_port = int(port)
        self.transport = transport
        self._forward_server = None
        self._hostname = "localhost"
        self._local_bind_port = None

    def start(self):
        logging.debug(f"starting tunnel to -> {self.remote_dns_name}:{self._local_bind_port}")
        self._start_tunnel()

    def stop(self):
        logging.debug(f"stopping tunnel from localhost:{self._local_bind_port} -> {self.remote_dns_name}:{self._local_bind_port}")
        self._forward_server.shutdown()

    @property
    def local_endpoint(self):
        return f"{self._hostname}:{self._local_bind_port}"

    @property
    def host_port(self):
        return (self._hostname, self._local_bind_port)

    @property
    def local_port(self):
        return self._local_bind_port


    def _start_tunnel(self):
        self._forward_server, self._local_bind_port = self.try_start_tunnel(self.remote_dns_name, self.remote_port, self.transport)

    @staticmethod
    def try_start_tunnel(remote_host, remote_port, ssh_transport, local_port=0):
        class SubHander(Handler):
            chain_host = remote_host
            chain_port = remote_port
            transport = ssh_transport
            local_bind_port = local_port

            def __init__(self, request, client_address, server):
                logging.debug(f"initing <<{remote_host}>> subhandler: {client_address} -> {server.server_address} ")
                super().__init__(request, client_address, server)

            def finish(self):
                logging.debug(f'finishing <<{remote_host}>> subhandler: {self.server.server_address}')
                return SocketServer.BaseRequestHandler.finish(self)

        forward_server = ForwardServer(("", local_port), SubHander)
        selected_port = forward_server.server_address[1]
        server_thread = threading.Thread(target=forward_server.serve_forever, daemon=True)
        server_thread.start()
        return forward_server, selected_port


class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            logging.debug(f"handler request.peername(): {self.request.getpeername()}")
            logging.debug(
                f"Handling SocketServer {self.server.server_address} -> ({self.chain_host}:{self.chain_port})")
            chan = self.transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername(),
            )
        except Exception as e:
            logging.error(
                "Error in SocketServer handler trying to open_channel: Incoming request to %s:%d was rejected by the SSH server."
                % (self.chain_host, self.chain_port)
            )
            return

        if chan is None:
            logging.error(
                "Error in SockerServer handler trying to open_channel: Channel is None"
                % (self.chain_host, self.chain_port)
            )
            return

        logging.debug(
            "Connected! handler client %r functioning for (%r) -> %r -> %r"
            % (
                self.request.getpeername(),
                f"localhost:{self.local_bind_port}",
                chan.getpeername(),
                (self.chain_host, self.chain_port),
            )
        )
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        request_peername = self.request.getpeername()
        chan.close()
        self.request.close()
        logging.debug("Handler client %r closed from (%r) <- %r" % (request_peername, f"localhost:{self.local_bind_port}", (self.chain_host, self.chain_port)))


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
