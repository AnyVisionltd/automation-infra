import json

from munch import *
import pytest

from infra.model.base_config import BaseConfig


def pytest_addoption(parser):
    parser.addoption(
        "--alias",
        action="store",
        default="config1",
        help="configuration alias",
    )
    parser.addoption(
        "--ip",
        action="store",
        default="0.0.0.0",
        help="host ip address",
    )
    parser.addoption(
        "--setup_only",
        action="store_true",
        help="only do hardware setup or also run tests"
    )
    parser.addoption(
        "--cluster_config",
        action="store",
        default="cluster1",
        help="cluster alias",
    )
# TODO: add like another million of these instead of base_config.json???


@pytest.fixture(scope='session')
def base_config(request):
    config = json.loads(request.config.getoption('--cluster_config'))
    base_config = BaseConfig.fromDict(config, DefaultFactoryMunch)
    # for host in base_config.cluster.hosts:
    #     pass
    #     # TODO: init ssh
    # TODO: init communication docker container
    # TODO: switch if working in docker/k8s
    return base_config
