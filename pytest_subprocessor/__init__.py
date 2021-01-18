import copy
import queue
import threading

from plumbum import local
import sys
import uuid
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import json
import logging
import os
import subprocess
from concurrent import futures
from json import JSONDecodeError

import pytest
from _pytest.outcomes import Exit
from _pytest.runner import CallInfo

from infra.utils.plugin_logging import InfraFormatter
from .worker import Worker

SESSION_ID_ENV_VAR = "HABERTEST_SESSION_ID"
ITEM_ID_ENV_VAR = "HABERTEST_ITEM_ID"
SERIALIZED_REPORT_LOCATION = '/tmp/habertest_infra_reports'


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_parse(pluginmanager, args):
    if not any(['--logs-dir' in arg for arg in args]):
        now = datetime.now().strftime("%Y_%m_%d__%H%M_%S")
        args.append(f'--logs-dir=logs/{now}')
    if not any(['--html' in arg for arg in args]):
        args.extend([f'--html=logs/{now}/report.html', '--self-contained-html'])


def pytest_addoption(parser):
    group = parser.getgroup("pytest_subprocessor")
    group.addoption("--num-parallel", type=int, default=1,
                     help="number of resourcess to provision and run tests against in parallel")
    group.addoption("--logs-dir", action="store", default=f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}', help="custom directory to store logs in")
    group.addoption("--sf", dest="secondary_flags", action="append", default=[],
                     help='flags to pass to the secondary pytest call (after provisioning).'
                          'Can be passed individually like --sf=-flag1 --sf=--flag2 or with escaped " marks like '
                          '--sf=\\"--flag1 value1 --flag2\\"')


def pytest_addhooks(pluginmanager):
    from pytest_subprocessor import hooks
    pluginmanager.add_hookspecs(hooks)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    configure_logging(config)


def configure_logging(config):
    custom_logs_dir = config.getoption("--logs-dir")
    session_logs_dir = custom_logs_dir
    os.makedirs(session_logs_dir, exist_ok=True)
    config.option.logger_logsdir = session_logs_dir

    main_process_logs_dir = f'{config.option.logger_logsdir}/main_process'
    os.makedirs(main_process_logs_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(InfraFormatter())
    root_logger.addHandler(console_handler)

    debug_file_handler = logging.FileHandler(f'{main_process_logs_dir}/debug.log', mode='w')
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(InfraFormatter())
    root_logger.addHandler(debug_file_handler)

    info_file_handler = logging.FileHandler(f'{main_process_logs_dir}/info.log', mode='w')
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(InfraFormatter())
    root_logger.addHandler(info_file_handler)


def pytest_sessionstart(session):
    # This is to be able to have the idea of a test "session" as pytest uses it,
    # even if tests are run on separate pytest calls on different processes:
    session.id = str(uuid.uuid4())
    os.environ[SESSION_ID_ENV_VAR] = session.id
    logging.debug(f"session_id: {session.id}")
    session.tests_queue = queue.Queue()


@pytest.hookimpl(tryfirst=True)
def pytest_runtestloop(session):
    """
    This is the (interesting part of the) pytest implementation of runtest_loop:
    ├── pytest_runtestloop
    │   └── pytest_runtest_protocol
    │       ├── pytest_runtest_logstart
    │       ├── pytest_runtest_setup
    │       │   └── pytest_fixture_setup
    │       ├── pytest_runtest_makereport
    │       ├── pytest_runtest_logreport
    │       │   └── pytest_report_teststatus
    │       ├── pytest_runtest_call
    │       │   └── pytest_pyfunc_call
    │       ├── pytest_runtest_teardown
    │       │   └── pytest_fixture_post_finalizer
    │       └── pytest_runtest_logfinish

    In this plugin, we implement our own version of runtest_protocol which runs before pytest default implementation
    (tryfirst=True), which builds and calls pytest commands of gathered tests on a subprocess.

    After the subprocess finishes, the pytest default implementation hook is called, which triggeres runtest_protocol
    hook, which we implement further down in this module.
    """
    if session.testsfailed and not session.config.option.continue_on_collection_errors:
        raise session.Interrupted("%d errors during collection" % session.testsfailed)

    if session.config.option.collectonly:
        return True

    workers = list()
    for i in range(session.config.option.num_parallel):
        worker = Worker(session)
        workers.append(worker)

    session.config.hook.pytest_build_items_iter(session=session, workers=workers)

    for worker in workers:
        logging.debug(f"starting worker {worker.id}")
        worker.start()

    for fut in futures.as_completed([worker.completion for worker in workers]):
        logging.debug("waiting for futures to complete")
        try:
            fut.result()
            for i, item in enumerate(fut.worker.handled_items):
                nextitem = fut.worker.handled_items[i + 1] if i + 1 < len(fut.worker.handled_items) else None
                session.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
        except:
            raise

        if session.shouldfail:
            raise session.Failed(session.shouldfail)
        if session.shouldstop:
            raise session.Interrupted(session.shouldstop)

    # TODO: add another pytest command which says only run post-mortem hoooks
    # At this point the tests have run and wrote their serialized reports to disk on /tmp/habertest...
    # using pytest_report_from_serializable
    return True


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    """
    This hook is a firstResult hook, which means it stops calling other hooks when 1 hook implementation returns a
     value. We return True at the end of this implementation, and we run first (tryfirst=True), therefore pytests
     implementation of this hook WILL NOT BE TRIGGERED.

    In pytests implementation, the hook calls the 2 log hooks (logstart and logfinish) which we call here as well,
     but in the middle it (basically) calls call_and_report for each item.

    We have already called the test items our runtest_loop we implemented up above in this module, so the items already
     ran and all we need to do is collect the serialized reports.

    REMINDER: the tests have already run on a subprocess in the runtest_loop.
    """
    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    # here all we really need to do is collect the reports already written to disk by the child
    # which ran the actual tests..
    run_fictitious_testprotocol(item)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    return True


def run_fictitious_testprotocol(item):
    """
    REMINDER: Tests have already run on subprocess. Here we just need to convince the current pytest process that
    the tests have already run and to collect their reports.
    """
    call = CallInfo.from_call(
        lambda: True, when="setup", reraise=(Exit,)
    )
    item.ihook.pytest_runtest_makereport(item=item, call=call)
    call = CallInfo.from_call(
        lambda: True, when="call", reraise=(Exit,)
    )
    item.ihook.pytest_runtest_makereport(item=item, call=call)
    call = CallInfo.from_call(
        lambda: True, when="teardown", reraise=(Exit,)
    )
    item.ihook.pytest_runtest_makereport(item=item, call=call)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    REMINDER: We already invoked the tests on a subprocess. The tests after they ran serialized the reports onto
    the disk, so here we just need to deserialize the existing reports, and attach them to the existing "test run".
    """
    report = report_from_disk(item, call)
    if not report:
        return None

    # After getting the report, we need to log it and report the teststatus so that the current pytest_session
    # will believe acknowledge that the tests ran.
    # We need to call these hooks because they are called by pytests implementation of runtest_protocol which we
    # overode, such that if we dont call the hooks ourselves no one will.

    item.ihook.pytest_runtest_logreport(report=report)
    item.ihook.pytest_report_teststatus(report=report, config=item.config)
    return report


def report_from_disk(item, call):
    """The tests have been run via pytest subprocess, which writes serialized reports to the disk.
    All thats left to do is read from the disk and deserialize :) """
    report_file = serialized_path(item, call) # f'{SERIALIZED_REPORT_LOCATION}/{item.nodeid.replace("/", "-").replace(":", "..")}.{call.when}.report'
    if not os.path.exists(report_file):
        # This probably means the subprocess test run froze/timed_out/got fucked somehow:
        logging.error(f"report: {report_file} doesnt exists")
        item.teardown()
        return
    with open(report_file, 'r') as f:
        report_ser = json.load(f)
    report = item.config.hook.pytest_report_from_serializable(data=report_ser, config=item.config)
    os.remove(report_file)
    return report


def serialized_path(item, call):
    return f'{SERIALIZED_REPORT_LOCATION}/{item.id}.{call.when}.report'


@pytest.hookimpl(trylast=True)
def pytest_build_items_iter(session, workers):
    logging.debug("subprocessor building items_iter. This is the trivial case and shouldn't usually happen..")
    session.tests_queue.queue = queue.deque(session.items)


@pytest.hookimpl(trylast=True)
def pytest_get_next_item(session, worker):
    logging.debug("trying to get_next_item via trivial implementation")
    try:
        item = session.tests_queue.get(block=False)
        logging.debug(f"trivial implementation returning item {os.path.split(item.nodeid)[1]}.. "
                      f"This shouldn't usually happen")
        return item
    except queue.Empty:
        return None
