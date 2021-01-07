import json
import logging
import os
from datetime import datetime

import pytest
from _pytest.reports import TestReport

from infra.utils.plugin_logging import InfraFormatter
import pytest_subprocessor


def pytest_addoption(parser):
    parser.addoption("--logs-dir", action="store", default=f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}',
                     help="custom directory to store logs in")
    parser.addoption("--item-id", action="store", help="item_id to use to serialize report")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    configure_logging(config)


def configure_logging(config):
    session_logs_dir = config.getoption("--logs-dir")
    os.makedirs(session_logs_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(InfraFormatter())
    root_logger.addHandler(console_handler)

    debug_file_handler = logging.FileHandler(f'{session_logs_dir}/debug.log', mode='w')
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(InfraFormatter())
    root_logger.addHandler(debug_file_handler)

    info_file_handler = logging.FileHandler(f'{session_logs_dir}/info.log', mode='w')
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(InfraFormatter())
    root_logger.addHandler(info_file_handler)


def pytest_sessionstart(session):
    session.id = os.environ.get(pytest_subprocessor.SESSION_ID_ENV_VAR, None)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    item.id = item.config.option.item_id


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    report = TestReport.from_item_and_call(item, call)
    report_ser = item.config.hook.pytest_report_to_serializable(report=report, config=item.config)
    os.makedirs(pytest_subprocessor.SERIALIZED_REPORT_LOCATION, exist_ok=True)
    with open(pytest_subprocessor.serialized_path(item, call),  'w') as f:
        json.dump(report_ser, f)



