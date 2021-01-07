import copy
import time
from datetime import datetime
import json
import logging
import os
import threading

import pytest

from infra.model.groups import Group
from infra.utils import ssh_agent
from pytest_provisioner.heartbeat_client import HeartbeatClient
from pytest_provisioner.provisioner_client import ProvisionerClient


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_parse(pluginmanager, args):
    if not any(['--logs-dir' in arg for arg in args]):
        now = datetime.now().strftime("%Y_%m_%d__%H%M_%S")
        args.append(f'--logs-dir=logs/{now}')
    if not any(['--html' in arg for arg in args]):
        args.extend([f'--html=logs/{now}/report.html', '--self-contained-html'])


def pytest_addoption(parser):
    parser.addoption("--provisioner", type=str,
                     help="endpoint of provisioning service to get hardware to run tests on, incl http/s")
    parser.addoption("--heartbeat", type=str,
                     help="endpoint of heartbeat service to get hardware to run tests on, incl http/s")
    parser.addoption("--ssl-cert", type=str, default='',
                     help="path to ssl-cert to use for ssl auth")
    parser.addoption("--ssl-key", type=str, default='',
                     help="path to ssl-key to use for ssl auth")


def pytest_addhooks(pluginmanager):
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


def pytest_sessionstart(session):
    ssh_agent.setup_agent()
    provisioner = session.config.getoption("--provisioner")
    assert provisioner, "the following arguments are required: --provisioner"
    cert = session.config.getoption("--ssl-cert")
    key = session.config.getoption("--ssl-key")
    session.provisioner = ProvisionerClient(ep=provisioner, cert=cert, key=key)


def pytest_collection_modifyitems(session, config, items):
    config.hook.pytest_before_group_items(session=session, config=config, items=items)
    group_tests(session, items, config.hook)
    config.hook.pytest_after_group_items(session=session, config=config, items=items)

    # TODO: set test.teardown() property?


def group_tests(session, items, hook):
    session.groups = list()
    Group.assign_to_new_group(items[0], session.groups)
    for idx in range(1, len(items)):
        for group in session.groups:
            together = hook.pytest_can_run_together(item1=group.tests[0], item2=items[idx])
            if together:
                group.attach(items[idx])
                break
        if not getattr(items[idx], "test_group", None):
            Group.assign_to_new_group(items[idx], session.groups)

    logging.info(f"groups: {[group.tests for group in session.groups]}")
    if len(session.groups) < session.config.option.num_parallel:
        session.groups = Group.reorganize(session.groups, session.config.option.num_parallel)
        logging.info(f"groups were shuffled as num_parallel is higher than groups: "
                     f"{[len(group.tests) for group in session.groups]}")


@pytest.hookimpl(tryfirst=True)
def pytest_start_subprocess(item):
    try:
        group = item.test_group
        if not group.provisioned_hardware:
            item.config.hook.pytest_before_provisioning(item=item)
            provision_hardware(item)
            item.config.hook.pytest_after_provisioning(item=item)
        item.config.option.secondary_flags.extend(["--provisioned-hardware", json.dumps(group.provisioned_hardware, separators=(',', ':'))])
    except:
        logging.error("couldnt provision hardware. exiting...")
        os._exit(666)


def provision_hardware(item):
    session = item.session
    logging.debug("provisioning hardware")
    hardware = session.provisioner.provision(item.function.__hardware_reqs)
    logging.info(f"provisioned hardware: {hardware_to_print(hardware)}")
    os.environ["HABERTEST_ALLOCATION_ID"] = hardware['allocation_id']
    item.test_group.provisioned_hardware = hardware
    item.test_group.kill_hb = threading.Event()
    hb = HeartbeatClient(stop=item.test_group.kill_hb,
                         ep=session.config.getoption("--heartbeat"),
                         cert=session.config.getoption("--ssl-cert"),
                         key=session.config.getoption("--ssl-key"))
    logging.debug("Success! Sending heartbeat")
    hb.send_heartbeats_on_thread(hardware['allocation_id'])
    return hardware


def hardware_to_print(hardware):
    hw = copy.deepcopy(hardware)
    # remove pem_key_string bc its junks up the terminal:
    [host.pop("pem_key_string", None) for name, host in hw['machines'].items()]
    hw = {name: host for name, host in hw['machines'].items()}
    return hw


@pytest.hookimpl(trylast=True)
def pytest_end_subprocess(item):
    group = item.test_group
    for item in group.tests:
        if not getattr(item, "ran", None):
            return
    logging.debug(f"All tests in group {group.id} ran. Releasing hardware...")
    release_hardware(item)


def release_hardware(item):
    item.test_group.kill_hb.set()
    time.sleep(5)
    item.session.provisioner.release(item.test_group.provisioned_hardware['allocation_id'])
    logging.info(f"released hardware: {hardware_to_print(item.test_group.provisioned_hardware)}")


@pytest.hookimpl(trylast=True)
def pytest_can_run_together(item1, item2):
    """
    This is default implementation if no one else implemented this hook.
    It does a trivial comparison of hardware_reqs adn cluster_config.
    """
    if item1.function.__hardware_reqs == item2.function.__hardware_reqs and \
            item2.function.__cluster_config == item2.function.__cluster_config:
        return True
    return False