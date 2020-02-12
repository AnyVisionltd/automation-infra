# -*- coding: utf-8 -*-
import logging
import os

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_base_plugin_fixture(base_config):
    logging.info(f"PID of base_plugin_fixture: {os.getpid()}")
    logging.info(base_config.hosts.host)
    logging.info(f"inside test: successfully initialized hardware")
