import logging
import pytest

from automation_infra.utils.initializer import init_plugins


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    logging.info("running infra pre-test cleaner.")
    hosts = item.funcargs['base_config'].hosts
    for name, host in hosts.items():
        # TODO: multi-thread this
        init_plugins(host)
        host.clean_between_tests()
