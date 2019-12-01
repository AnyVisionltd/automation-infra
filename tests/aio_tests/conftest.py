import json

from munch import *
import pytest
from paramiko.ssh_exception import NoValidConnectionsError

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from infra.model import host as host_module
from runner import CONSTS

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


def connect_via_running_docker(base):
    base.host.SSH.connect(CONSTS.TUNNEL_PORT)


def init_docker_and_connect(base):
    print("initializing docker")
    base.host.SSH.connect()
    docker_args = ['pem', base.host.user] if base.host.keyfile else ['password', base.host.user, base.host.password]
    deploy_proxy_container(base.host.SSH, docker_args)
    base.host.SSH.connect(CONSTS.TUNNEL_PORT)
    print("docker is running and ssh connected")


def tear_down_docker(base):
    print("tearing down docker")
    base.host.SSH.connect()
    remove_proxy_container(base.host.SSH)
    print("docker is stopped and disconnected")


@pytest.fixture(scope='session')
def base_config(request):
    print("initing base config..")
    config = json.loads(request.config.getoption('--sut_config'))
    base = BaseConfig.fromDict(config, DefaultFactoryMunch)
    base.host = Host(base.host)
    try:
        connect_via_running_docker(base)
        yield base
    except NoValidConnectionsError:
        init_docker_and_connect(base)
        yield base
        # TODO: switch if working in docker/k8s
        tear_down_docker(base)


def test_functionality(base_config):
    print("successfully inited fixture!")
    assert 1

