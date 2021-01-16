import concurrent
import contextlib
import logging
import select
import socket
import time
import threading

from paramiko import SSHException

from automation_infra.utils import waiter
import sys
import paramiko

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer


class Tunnel(object):
    def __init__(self, dns_name, port, transport, local_bind_port=None):
        self.remote_dns_name = dns_name
        self.remote_port = int(port)
        self.transport = transport
        self._forward_server = None
        self._hostname = "localhost"
        self._local_bind_port = local_bind_port or 0

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
        self._forward_server, self._local_bind_port = waiter.wait_nothrow(lambda:
                            self.try_start_tunnel(self.remote_dns_name, self.remote_port, self.transport, self._local_bind_port))


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
                is_in_error = sys.exc_info()[0] is not None
                logging.debug(f'finishing <<{remote_host}>> subhandler: {self.server.server_address} error ? {is_in_error}')
                return SocketServer.BaseRequestHandler.finish(self)

        forward_server = ForwardServer(("", local_port), SubHander)
        selected_port = forward_server.server_address[1]
        server_thread = threading.Thread(target=forward_server.serve_forever, daemon=True)

        server_thread.start()
        return forward_server, selected_port


class Handler(SocketServer.BaseRequestHandler):
    RECV_BUFFER_SIZE  = 4 * 1024 * 1024
    def handle(self, attempt=0, err=None):
        attempt = attempt + 1
        if attempt >= 3:
            logging.error("Too many attempts made!")
            return err
        try:
            chan = self.transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername(),
                max_packet_size = paramiko.common.MAX_WINDOW_SIZE
            )
            if chan is None:
                message = "Error in SockerServer handler trying to open_channel: %s:%d Channel is None" % (
                    self.chain_host, self.chain_port)
                logging.error(message)
                return

            while chan.active:
                r, w, x = select.select([self.request, chan], [], [])
                if self.request in r:
                    data = self.request.recv(Handler.RECV_BUFFER_SIZE)
                    if len(data) == 0:
                        break
                    chan.sendall(data)
                if chan in r:
                    if not chan.recv_ready():
                        break
                    data = chan.recv(Handler.RECV_BUFFER_SIZE)
                    self.request.sendall(data)
            chan.close()
            self.request.close()
        except (ConnectionResetError, EOFError, SSHException) as err:
            time.sleep(1)
            self.handle(attempt, err)
        except OSError:
            # this gets thrown when connection is reset and then when trying to get request.getpeername() thrown again
            # theres nothing to handle here, just makes logs a bit nicer.
            pass
        except Exception as err:
            logging.exception("Unknown error: %s", type(err))
            time.sleep(1)
            self.handle(attempt, err)


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
