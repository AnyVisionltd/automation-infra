import json

from munch import *
import pytest

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from infra.model import host as host_module
from runner import CONSTS


def pytest_addoption(parser):
    parser.addoption(
        "--sut_config",
        action="store",
        default="""{ "host":
            {
                "ip": "192.168.21.163",
                "user": "root",
                "password": "",
                "key_file_path": "/home/ori/Projects/automation-infra/runner/docker_build/docker_user.pem",
                "alias": "monster",
                "host_id": 123,
                "host_type": "physical",
                "allocation_id": ""
            }
        }
        """,
        help="ip user/pass config details",
    )


def run_proxy_container(connected_ssh_module):
    res = connected_ssh_module.execute('mkdir -p /tmp/build')
    res = connected_ssh_module.put('./runner/docker_build/Dockerfile', '/tmp/build')
    res = connected_ssh_module.put('./runner/docker_build/docker-compose.yml', '/tmp/build')
    res = connected_ssh_module.execute('docker build -t automation-tests:0.1 /tmp/build')
    res = connected_ssh_module.execute('docker-compose -f /tmp/build/docker-compose.yml up -d')
    print(res)


def remove_proxy_container(connected_ssh_module):
    res = connected_ssh_module.execute('docker-compose -f /tmp/build/docker-compose.yml down')
    print(res)


@pytest.fixture(scope='session')
def base_config(request):
    config = json.loads(request.config.getoption('--sut_config'))
    base = BaseConfig.fromDict(config, DefaultFactoryMunch)
    # The SSH and the SSH_host dont need to be separate, they can just be initialized on diff ports (default is 22)..
    run_proxy_container(host.SSH)
    base.host = Host(base.host)
    base.host.SSH.connect()
    base.host.SSH.connect(CONSTS.TUNNEL_PORT)
    # TODO: switch if working in docker/k8s
    yield base
    base.host.SSH.connect()
    remove_proxy_container(base.host.SSH)


def verify_fuctionality():
    h = host_module.init_example_host()
    h.SSH.connect()
    run_proxy_container(h.SSH)
    h.SSH.connect(CONSTS.TUNNEL_PORT)
    h.SSH.connect()
    remove_proxy_container(h.SSH)


if __name__ == '__main__':
    verify_fuctionality()


