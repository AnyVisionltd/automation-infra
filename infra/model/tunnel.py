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
                super().__init__(self.transport, request, client_address, server)

        forward_server = ForwardServer(("", local_port), SubHander)
        selected_port = forward_server.server_address[1]
        server_thread = threading.Thread(target=forward_server.serve_forever, daemon=True)

        server_thread.start()
        return forward_server, selected_port


class Handler(SocketServer.BaseRequestHandler):
    def __init__(self, transport, request, client_address, server):
        self.channel = None
        try:
            self.channel = transport.open_channel("direct-tcpip", (self.chain_host, self.chain_port), request.getpeername())
        except:
            pass
        super().__init__(request, client_address, server)

    def finish(self):
        if self.channel:
            self.channel.close()

    def handle(self):
        if not self.channel:
            logging.debug(f"Tunnel not connected {self.client_address[0]}:{self.client_address[1]}")
            return
        try:
            while True:
                r, w, x = select.select([self.request, self.channel], [], [])
                if self.request in r:
                    data = self.request.recv(1024)
                    if len(data) == 0:
                        break
                    self.channel.send(data)
                if self.channel in r:
                    data = self.channel.recv(1024)
                    if len(data) == 0:
                        break
                    self.request.send(data)
        except paramiko.ssh_exception.ChannelException:
            logging.debug(f"Channel exception on {self.client_address[0]}:{self.client_address[1]}", exc_info=True)
        except:
            logging.exception(f"Error during channel operation on {self.client_address[0]}:{self.client_address[1]}")
            raise


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
