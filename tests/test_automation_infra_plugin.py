# -*- coding: utf-8 -*-
import logging
import os
import time

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"ori_pass": {"gpu": 1, "ram": 16}, "ori_pem": {}})
def test_base_plugin_fixture(base_config):
    logging.warning(f"PID of base_plugin_fixture: {os.getpid()}")
    print(base_config.hosts.ori_pass)
    print(f"inside test: successfully initialized hardware")
    time.sleep(1)
    #assert False
