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
import uuid

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
        self._hostname = "127.0.0.1"
        self._local_bind_port = local_bind_port or 0

    def start(self):
        logging.debug(f"starting tunnel to -> {self.remote_dns_name}:{self._local_bind_port}")
        self._start_tunnel()

    def stop(self):
        logging.debug(f"stopping tunnel from {self._hostname}:{self._local_bind_port} -> {self.remote_dns_name}:{self._local_bind_port}")
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

        forward_server = ForwardServer(("", local_port), SubHander)
        selected_port = forward_server.server_address[1]
        server_thread = threading.Thread(target=forward_server.serve_forever, daemon=True)

        server_thread.start()
        return forward_server, selected_port


class Handler(SocketServer.BaseRequestHandler):
    RECV_BUFFER_SIZE = 4 * 1024 * 1024

    def _redirect(self, chan):
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

    def _retry_open_channel(self, timeout):
        end_time = time.time() + timeout
        last_exception = None
        while time.time() < end_time:
            try:
                return self.transport.open_channel(
                    "direct-tcpip",
                    (self.chain_host, self.chain_port),
                    self.request.getpeername(),
                    max_packet_size=paramiko.common.MAX_WINDOW_SIZE,
                    timeout=timeout)
            except:
                logging.debug(f"Failed to connect to {self.chain_host}:{self.chain_port}")
                last_exception = sys.exc_info()[1]
                time.sleep(1)
                pass
        else:
            raise last_exception

    def handle(self):
        connection_uuid = str(uuid.uuid4())
        connection_info = f"id: {connection_uuid} local {self.client_address} <-> remote {self.chain_host}:{self.chain_port}"
        logging.debug(f"Open tunnel on {connection_info}")
        try:
            chan = self._retry_open_channel(timeout=10)
        except Exception as e:
            msg_tupe = 'ssh ' if isinstance(e, paramiko.SSHException) else ''
            exc_msg = 'open new channel {0}error: {1}'.format(msg_tupe, e)
            msg = f"{connection_info} error: {exc_msg}"
            raise Exception(msg)

        connection_info = f"id: {connection_uuid} chanel id: {chan.chanid} remote channel id {chan.remote_chanid} local {self.client_address} <-> remote {self.chain_host}:{self.chain_port}"
        logging.debug(f"Tunnel {connection_info} connected")
        try:
            self._redirect(chan)
        except socket.error:
            # Sometimes a RST is sent and a socket error is raised, treat this
            # exception. It was seen that a 3way FIN is processed later on, so
            # no need to make an ordered close of the connection here or raise
            # the exception beyond this point...
            logging.debug(f"socket error in {connection_info}")
        except Exception as e:
            logging.debug(f"Error on {connection_info}")
        finally:
            logging.debug(f"Tunnel {connection_info} closed")
            chan.close()
            self.request.close()


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
