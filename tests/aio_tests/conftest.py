import json
import socket

from munch import *
import pytest

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from runner import helpers, hardware_initializer

#import sys
#sys.stdout = sys.stderr

EXAMPLE_IP = '0.0.0.0'

host_config_example1 = """{"host": {
    "ip": "%s",
    "user": "user",
    "password": "pass",
    "key_file_path": "",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
    }}""" % EXAMPLE_IP

host_config_example2 = """{"host": {
    "ip": "%s",
    "user": "root",
    "password": "",
    "key_file_path": "runner/docker_build/docker_user.pem",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}}""" % EXAMPLE_IP


@pytest.hookimpl()
def pytest_runtest_setup(item):
    # TODO: I cant run 2 tests with 1 hardware without reinitializing it.
    hardware_config = hardware_initializer.init_hardware(item.function.__hardware_reqs)
    item.function.__initialized_hardware = json.loads(hardware_config)


@pytest.fixture(scope='function')
def base_config(request):
    print("initing base config..")
    base = BaseConfig.fromDict(request.function.__initialized_hardware, DefaultFactoryMunch)
    base.host = Host(base.host)
    try:
        helpers.connect_via_running_docker(base)
        yield base
    except Exception:
        helpers.init_docker_and_connect(base)
        yield base
        # TODO: switch if working in docker/k8s
        helpers.tear_down_docker(base)


def test_functionality(base_config):
    print("successfully inited fixture!")
    assert 1

