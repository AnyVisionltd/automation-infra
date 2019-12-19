# -*- coding: utf-8 -*-
import pytest

from runner.helpers import hardware_config

pytest_plugins = "pytest_automation_infra"


@hardware_config(hardware={"type": "ori_pem"})
def test_base_plugin_fixture(base_config):
    print(base_config.host)
    print(f"successfully initialized hardware")


@pytest.mark.xfail
def test_should_fail():
    print("failed because I dont have hardware config!")

