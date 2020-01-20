import logging
import select
import threading

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer


def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername(),
            )
        except Exception as e:
            raise Exception(
                "Exception trying to open_channel to %s:%d failed: %s"
                % (self.chain_host, self.chain_port, repr(e))
            )
        if chan is None:
            raise Exception(
                "Error trying to open_channel: Incoming request to %s:%d was rejected by the SSH server."
                % (self.chain_host, self.chain_port)
            )

        logging.info(
            "Connected!  Tunnel open %r -> %r -> %r"
            % (
                self.request.getpeername(),
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

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        logging.info("Tunnel closed from %r" % (peername,))


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_tunnel(remote_host, remote_port, transport):
    class SubHander(Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport

    local_port = get_open_port()
    forward_server = ForwardServer(("", local_port), SubHander)
    server_thread = threading.Thread(target=forward_server.serve_forever, daemon=True)
    server_thread.start()
    return forward_server, local_port
