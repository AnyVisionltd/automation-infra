import logging
from pytest_automation_infra.helpers import hardware_config
import paramiko
import requests


@hardware_config(hardware={"host": {}})
def test_tunnel(base_config):
    host = base_config.hosts.host
    consul_tunnel = host.TunnelManager.get_or_create("remote", host.ip, 22)
    logging.info(f"tunnel up on: {consul_tunnel.host_port}")


@hardware_config(hardware={"host": {}})
def test_tunnel_ssh(base_config):
    host = base_config.hosts.host
    tunnel = host.TunnelManager.get_or_create("remote", host.ip, 2222)
    tunnel.local_endpoint

    logging.info("Try to create multiple sessions on tunnel")
    for i in range(100):
        client = paramiko.SSHClient()
        client.known_hosts = None
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"Connecting via tunnel try {i}")
        client.connect(hostname="127.0.0.1", port=tunnel.local_port, username="root", password="root", look_for_keys=False, allow_agent=False, timeout=10, auth_timeout=60)
        client.exec_command("true")
        client.close()


@hardware_config(hardware={"host": {}})
def test_tunnel_http(base_config):
    host = base_config.hosts.host
    http_server = host.SSH.run_background_script("python3 -m http.server 8000")
    tunnel = host.TunnelManager.get_or_create("remote", "localhost", 8000)

    for _ in range(100):
        requests.get(f"http://{tunnel.local_endpoint}/")

    http_server.kill()

