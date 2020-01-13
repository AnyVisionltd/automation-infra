# -*- coding: utf-8 -*-
import logging
import os
import time

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {"gpu": 1, "ram": 16}, "host2": {}})
def test_base_plugin_fixture(base_config):
    logging.info(f"PID of base_plugin_fixture: {os.getpid()}")
    logging.info(base_config.hosts.host)
    logging.info(base_config.hosts.host2)
    logging.info(f"inside test: successfully initialized hardware")
    time.sleep(5)


@hardware_config(hardware={"host3": {}})
def test_base_plugin_fixture2(base_config):
    logging.info(f"PID of base_plugin_fixture: {os.getpid()}")
    logging.info(base_config.hosts.host3)
    logging.info(f"inside test: successfully initialized hardware")
    time.sleep(5)
