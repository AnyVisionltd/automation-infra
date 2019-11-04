import json

from munch import *
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--ip",
        action="store",
        default="0.0.0.0",
        help="host ip address",
    )
# TODO: add like another million of these instead of base_config.json???


@pytest.fixture(scope='session')
def base_config(request):
    with open("base_config.json", 'r') as f:
        j = json.load(f)
    base_config = DefaultMunch.fromDict(j, DefaultMunch)
    return base_config


# TODO: what does this type of stuff do and when is it needed??
# def pytest_generate_tests(metafunc):
#     print(f"fixturenames: {metafunc.fixturenames}")
#     if "ip" in metafunc.fixturenames:
#         metafunc.parametrize("ip", metafunc.config.getoption("ip"))
