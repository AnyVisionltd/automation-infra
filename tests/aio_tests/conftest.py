import json

from munch import *
import pytest

from infra.model.host import Host


def pytest_addoption(parser):
    parser.addoption(
        "--sut_config",
        action="store",
        default="""
        {
            "ip": "192.168.20.34",
            "user": "user",
            "password": "pass",
            "key_file_path": "",
            "alias": "monster",
            "host_id": 123,
            "host_type": "physical",
            "allocation_id": ""
        }
        """,
        help="ip user/pass config details",
    )


@pytest.fixture(scope='session')
def host(request):
    config = json.loads(request.config.getoption('--sut_config'))
    host = Host(Munch.fromDict(config))
    # TODO: init communication docker container
    # TODO: switch if working in docker/k8s
    return host
