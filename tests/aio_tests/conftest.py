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


def deploy_proxy_container(connected_ssh_module, auth_args):
    # TODO: check if running instead of just trying to remove
    try:
        remove_proxy_container(connected_ssh_module)
    except:
        pass

    res = connected_ssh_module.execute('mkdir -p /tmp/build')
    res = connected_ssh_module.put('./runner/docker_build/Dockerfile', '/tmp/build')
    res = connected_ssh_module.put('./runner/docker_build/entrypoint.sh', '/tmp/build')

    image_tag = 'automation-tests:1.111'
    build_cmd = f'docker build -t {image_tag} /tmp/build'
    res = connected_ssh_module.execute(build_cmd)
    run_cmd = f'docker run -d --network=host --name=ssh_container {image_tag} {" ".join(auth_args)}'
    res = connected_ssh_module.execute(run_cmd)


def remove_proxy_container(connected_ssh_module):
    res = connected_ssh_module.execute(f'docker rm -f ssh_container')


@pytest.fixture(scope='session')
def base_config(request):
    config = json.loads(request.config.getoption('--sut_config'))
    base = BaseConfig.fromDict(config, DefaultFactoryMunch)
    base.host = Host(base.host)
    base.host.SSH.connect()
    docker_args = ['pem', base.host.user] if base.host.keyfile else ['password', base.host.user, base.host.password]
    deploy_proxy_container(base.host.SSH, docker_args)
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


