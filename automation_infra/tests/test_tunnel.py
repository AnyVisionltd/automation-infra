import logging

import pytest
from paramiko import SSHException

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_tunnel(base_config):
    host = base_config.hosts.host
    with pytest.raises(SSHException):
        failed_tunnel = host.TunnelManager.get_or_create("temp", "fake", 1234)
    consul_tunnel = host.TunnelManager.get_or_create("remote", host.ip, 22)
    logging.info(f"tunnel up on: {consul_tunnel.host_port}")
