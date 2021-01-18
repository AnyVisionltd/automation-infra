import copy
import time
from datetime import datetime
import json
import logging
import os
import threading

import pytest

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
    group = parser.getgroup("pytest_provisioner")
    group.addoption("--provisioner", type=str,
                     help="endpoint of provisioning service to get hardware to run tests on, incl http/s")
    group.addoption("--heartbeat", type=str,
                     help="endpoint of heartbeat service to get hardware to run tests on, incl http/s")
    group.addoption("--ssl-cert", type=str, default='',
                     help="path to ssl-cert to use for ssl auth")
    group.addoption("--ssl-key", type=str, default='',
                     help="path to ssl-key to use for ssl auth")


def pytest_addhooks(pluginmanager):
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


def pytest_configure(config):
    if config.pluginmanager.hasplugin('pytest_grouper'):
        from . import grouper_hooks
        config.pluginmanager.register(grouper_hooks)


def pytest_sessionstart(session):
    ssh_agent.setup_agent()
    provisioner = session.config.getoption("--provisioner")
    assert provisioner, "the following arguments are required: --provisioner"
    cert = session.config.getoption("--ssl-cert")
    key = session.config.getoption("--ssl-key")
    session.provisioner = ProvisionerClient(ep=provisioner, cert=cert, key=key)
    session.hardware_map = dict()  # {worker.id:{hardware:hardware, kill_hb: event()}}


@pytest.hookimpl(tryfirst=True)
def pytest_start_subprocess(item, worker):
    try:
        hardware = item.session.hardware_map.get(worker.id, None)
        if not hardware:
            item.config.hook.pytest_before_provisioning(item=item)
            provision_hardware(item, worker)
            item.config.hook.pytest_after_provisioning(item=item)
        item.config.option.secondary_flags.extend(["--provisioned-hardware",
                                                   json.dumps(item.session.hardware_map[worker.id]['hardware'],
                                                              separators=(',', ':'))])
    except:
        logging.error("couldnt provision hardware. exiting...")
        os._exit(666)


def provision_hardware(item, worker):
    session = item.session
    logging.info(f"provisioning hardware for item {os.path.split(item.nodeid)[1]}")
    hardware = session.provisioner.provision(item.function.__hardware_reqs)
    logging.info(f"provisioned hardware: {hardware_to_print(hardware)}")
    os.environ["HABERTEST_ALLOCATION_ID"] = hardware['allocation_id']
    item.session.hardware_map[worker.id] = {"hardware": hardware, "kill_hb": threading.Event()}
    hb = HeartbeatClient(stop=item.session.hardware_map[worker.id]['kill_hb'],
                         ep=session.config.getoption("--heartbeat"),
                         cert=session.config.getoption("--ssl-cert"),
                         key=session.config.getoption("--ssl-key"))
    logging.debug("Success! Sending heartbeat")
    hb.send_heartbeats_on_thread(hardware['allocation_id'])


def hardware_to_print(hardware):
    hw = copy.deepcopy(hardware)
    # remove pem_key_string bc its junks up the terminal:
    [host.pop("pem_key_string", None) for name, host in hw['machines'].items()]
    hw = {name: host for name, host in hw['machines'].items()}
    return hw


@pytest.hookimpl(trylast=True)
def pytest_end_subprocess(item, worker):
    # if pytest_grouper is registered, the proper place to release is in pytest_finished_handling_group hook
    # (which grouper calls). If the grouper isnt active, then each test is a "group" on its own, and we
    # must allocate/release for each item:
    if not item.config.pluginmanager.hasplugin('pytest_grouper'):
        logging.debug("running without pytest_grouper invoked and therefore releasing hardware at pytest_end_subprocess")
        release_worker_hardware(item.session, worker)


def release_worker_hardware(session, worker):
    do_release_hardware(session.provisioner,
                        session.hardware_map[worker.id]['hardware']['allocation_id'],
                        session.hardware_map[worker.id]['kill_hb'])
    del session.hardware_map[worker.id]


def do_release_hardware(provisioner_client, allocation_id, hb_stop):
    logging.info(f"releasing hardware {allocation_id}")
    hb_stop.set()
    time.sleep(5)
    provisioner_client.release(allocation_id)


