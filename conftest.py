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
# TODO: add like another million of these instead of base_config.json???


@pytest.fixture(scope='session')
def base_config(request):
    with open("base_config.json", 'r') as f:
        j = json.load(f)
    base_config = BaseConfig.fromDict(j, DefaultFactoryMunch)
    return base_config


@pytest.fixture(autouse=True)
def setup_only(request):
    return request.config.getoption("--setup_only")

