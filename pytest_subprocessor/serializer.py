import json
import logging
import os
import pathlib
from datetime import datetime

import pytest

from infra.utils.plugin_logging import InfraFormatter
import pytest_subprocessor
from pytest_subprocessor.worker import sanitize_nodeid


def pytest_addoption(parser):
    parser.addoption("--logs-dir", action="store", default=f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}',
                     help="custom directory to store logs in")
    parser.addoption("--item-id", action="store", help="item_id to use to serialize report")
    parser.addoption("--session-id", action="store", help="session_id to mark 'session' scoped fixtures")


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
    session.id = session.config.option.session_id


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    item.id = item.config.option.item_id


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report_ser = item.config.hook.pytest_report_to_serializable(report=report, config=item.config)
    os.makedirs(pytest_subprocessor.SERIALIZED_REPORT_LOCATION, exist_ok=True)
    with open(pytest_subprocessor.serialized_path(item, call),  'w') as f:
        json.dump(report_ser, f)
    if report.when == 'call':
        logging.info(f"\n>>>>>>>>>>{'.'.join(item.listnames()[-2:])} {'PASSED' if report.passed else 'FAILED'}")
        if report.failed:
            logging.info(report.longreprtext)
        create_symbolic_link(item, report.outcome)


def create_symbolic_link(item, outcome):
    item_logs_dir = os.path.realpath(item.config.getoption("--logs-dir"))
    if "test_logs" in item_logs_dir:
        test_logs_dir = pathlib.Path(item_logs_dir)
        while test_logs_dir.name != 'test_logs':
            test_logs_dir = test_logs_dir.parent
    else:
        test_logs_dir = pathlib.Path(item_logs_dir)
    by_outcome_dir = os.path.join(test_logs_dir, outcome)
    os.makedirs(by_outcome_dir, exist_ok=True)
    dest = os.path.realpath(os.path.join(by_outcome_dir, sanitize_nodeid(os.path.split(item.nodeid)[1])))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        os.symlink(os.path.relpath(item_logs_dir, os.path.dirname(dest)), dest, target_is_directory=True)
