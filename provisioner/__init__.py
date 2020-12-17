import logging
import os
import threading

import pytest

from infra.utils import ssh_agent
from pytest_automation_infra.heartbeat_client import HeartbeatClient
from pytest_automation_infra.provisioner_client import ProvisionerClient


def pytest_addoption(parser):
    parser.addoption("--provisioner", type=str,
                     help="endpoint of provisioning service to get hardware to run tests on, incl http/s")
    parser.addoption("--heartbeat", type=str,
                     help="endpoint of heartbeat service to get hardware to run tests on, incl http/s")
    parser.addoption("--ssl-cert", type=str, default='',
                     help="path to ssl-cert to use for ssl auth")
    parser.addoption("--ssl-key", type=str, default='',
                     help="path to ssl-key to use for ssl auth")


def pytest_sessionstart(session):
    session.kill_heartbeat = threading.Event()
    ssh_agent.setup_agent()
    provisioner = session.config.getoption("--provisioner")
    assert provisioner, "the following arguments are required: --provisioner"
    cert = session.config.getoption("--ssl-cert")
    key = session.config.getoption("--ssl-key")
    session.provisioner = ProvisionerClient(ep=provisioner, cert=cert, key=key)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    session = item.session
    logging.debug("Provisioning hardware")
    hardware = session.provisioner.provision(item.function.__hardware_reqs)
    os.environ["HABERTEST_ALLOCATION_ID"] = hardware['allocation_id']
    session.kill_heartbeat = threading.Event()
    hb = HeartbeatClient(stop=item._request.session.kill_heartbeat,
                         ep=session.config.getoption("--heartbeat"),
                         cert=session.config.getoption("--ssl-cert"),
                         key=session.config.getoption("--ssl-key"))
    logging.debug("Success! Sending heartbeat")
    hb.send_heartbeats_on_thread(hardware['allocation_id'])
    session.__initialized_hardware = hardware
    item.function.__initialized_hardware = hardware
    logging.debug("Resource available")
    yield


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    if not session.kill_heartbeat:
        return
    logging.debug("killing heartbeat")
    session.kill_heartbeat.set()
    logging.debug("releasing allocated resources")
    session.provisioner.release(session.__initialized_hardware['allocation_id'])