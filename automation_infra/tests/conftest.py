import concurrent
import logging
import os

import pytest

from automation_infra.utils import initializer as infra_initializer


def setup(host):
    infra_initializer.init_plugins(host)
    host.clean_between_tests()


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    logging.info("running infra pre-test cleaner.")
    hosts = item.funcargs['base_config'].hosts
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.environ.get('WORKERS', 4)) as executor:
        executor.map(setup, [host for name, host in hosts.items()])


