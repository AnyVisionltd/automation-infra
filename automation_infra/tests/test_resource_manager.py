import logging

from automation_infra.plugins.resource_manager import ResourceManager
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    manager = base_config.hosts.host.ResourceManager
    manager.verify_functionality()
