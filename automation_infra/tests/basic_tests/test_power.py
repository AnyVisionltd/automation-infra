import logging

import pytest

from automation_infra.plugins.power import Power

from automation_infra.utils import waiter
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_power_plugin(base_config):
    logging.info("starting power test")
    host = base_config.hosts.host
    power = host.Power
    logging.info("powering off")
    power.off()
    logging.info("powered off")
    assert power.status() == 'off'
    with pytest.raises(Exception):
        logging.info("trying to connect, should get exception")
        host.SshDirect.connect(timeout=3)

    logging.info("powered off successfully, powering on")
    power.on()
    logging.info("powered on, trying to connect")
    waiter.wait_nothrow(lambda: power.status() == 'on')
    waiter.wait_nothrow(host.SshDirect.connect, timeout=30)
    helpers.deploy_proxy_container(host.SshDirect)
    logging.info("connected succesfully, plugin working!")
