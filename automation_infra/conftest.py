import logging
import pytest

from automation_infra.utils import initializer as infra_initializer


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    logging.info("running infra pre-test cleaner.")
    hosts = item.funcargs['base_config'].hosts
    for name, host in hosts.items():
        # TODO: multi-thread this
        infra_initializer.init_plugins(host)
        host.clean_between_tests()
