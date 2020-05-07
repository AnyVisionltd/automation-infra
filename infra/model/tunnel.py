import logging
import select
import threading

from automation_infra.utils import waiter

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer
LOCK = threading.Lock()


def get_open_port():
    LOCK.acquire()
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


class Tunnel(object):
    def __init__(self, dns_name, port, transport):
        self.remote_dns_name = dns_name
        self.remote_port = port
        self.transport = transport
        self._forward_server = None
        self._hostname = "localhost"
        self._local_bind_port = None

    def start(self):
        logging.info(f"starting tunnel to -> {self.remote_dns_name}:{self._local_bind_port}")
        self._start_tunnel()

    def stop(self):
        logging.info(f"stopping tunnel from localhost:{self._local_bind_port} -> {self.remote_dns_name}:{self._local_bind_port}")
        self._safe_stop()

    def _safe_stop(self):
        try:
            with waiter.time_limit(3):
                self.server.shutdown()
                self.server.server_close()
        except TimeoutError:
            logging.error(f"Caught timeout trying to stop tunnel "
                         f"localhost:{self._local_bind_port} -> {self.remote_dns_name}:{self.remote_port} "
                         f"it probably was not running...")

    def _start_tunnel(self):
        try:
            self._forward_server, self._local_bind_port = self.try_start_tunnel(self.remote_dns_name, self.remote_port, self.transport, self.remote_port)
        except OSError:
            # local_bind port is taken so use random free port to communicate:
            self._forward_server, self._local_bind_port = self.try_start_tunnel(self.remote_dns_name, self.remote_port, self.transport)

    @staticmethod
    def try_start_tunnel(remote_host, remote_port, ssh_transport, local_port=None):
        class SubHander(Handler):
            chain_host = remote_host
            chain_port = remote_port
            transport = ssh_transport
            local_bind_port = local_port

            def __init__(self, request, client_address, server):
                logging.info(f"initing <<{remote_host}>> subhandler: {client_address} -> {server.server_address} ")
                super().__init__(request, client_address, server)

            def finish(self):
                logging.info(f'finishing <<{remote_host}>> subhandler: {self.server.server_address}')
                return SocketServer.BaseRequestHandler.finish(self)

        if local_port is None:
            local_port = get_open_port()
        forward_server = ForwardServer(("", local_port), SubHander)
        server_thread = threading.Thread(target=forward_server.serve_forever, daemon=True)
        server_thread.start()
        if LOCK.locked():
            LOCK.release()
        return forward_server, local_port


class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            logging.info(f"handler request.peername(): {self.request.getpeername()}")
            logging.info(
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

        logging.info(
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
        logging.info("Handler client %r closed from (%r) <- %r" % (request_peername, f"localhost:{self.local_bind_port}", (self.chain_host, self.chain_port)))


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
