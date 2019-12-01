import json

from munch import *
import pytest
from paramiko.ssh_exception import NoValidConnectionsError

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from infra.model import host as host_module
from runner import CONSTS

from runner import helpers

host_config_example1 = """{"host": {
    "ip": "%s",
    "user": "user",
    "password": "pass",
    "key_file_path": "",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
    }}""" % CONSTS.EXAMPLE_IP

host_config_example2 = """{"host": {
    "ip": "%s",
    "user": "root",
    "password": "",
    "key_file_path": "runner/docker_build/docker_user.pem",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}}""" % CONSTS.EXAMPLE_IP


def pytest_addoption(parser):
    parser.addoption(
        "--sut_config",
        action="store",
        default=host_config_example2,
        help="ip user/pass config details",
    )


@pytest.fixture(scope='session')
def base_config(request):
    print("initing base config..")
    config = json.loads(request.config.getoption('--sut_config'))
    base = BaseConfig.fromDict(config, DefaultFactoryMunch)
    base.host = Host(base.host)
    try:
        helpers.connect_via_running_docker(base)
        yield base
    except NoValidConnectionsError:
        helpers.init_docker_and_connect(base)
        yield base
        # TODO: switch if working in docker/k8s
        helpers.tear_down_docker(base)


def test_functionality(base_config):
    print("successfully inited fixture!")
    assert 1

