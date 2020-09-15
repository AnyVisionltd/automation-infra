# -*- coding: utf-8 -*-
import os
import logging
import re
import subprocess
import sys
import threading
import time
from datetime import datetime

import pytest
import requests
import yaml
from _pytest.fixtures import FixtureLookupError
from munch import *

from automation_infra.utils import initializer, concurrently
from infra.model.host import Host
from automation_infra.plugins.ssh import SSH
from automation_infra.plugins.ssh_direct import SshDirect
from pytest_automation_infra import provisioner_client, helpers, heartbeat_client
from pytest_automation_infra.helpers import is_k8s
from pytest_automation_infra.settings import infra_logger


class InfraFormatter(logging.Formatter):
    def __init__(self):
        msg_fmt = "%(asctime)20.20s.%(msecs)d %(threadName)-10.10s %(levelname)-6.6s %(message)-75s " \
              "%(funcName)-15.15s %(pathname)-70s:%(lineno)4d"
        logging.Formatter.__init__(self, msg_fmt, datefmt='%Y-%m-%d %H:%M:%S')


def pytest_addoption(parser):
    parser.addoption("--fixture-scope", type=str, default='auto', choices={"function", "module", "session", "auto"},
                     help="every how often to setup/tear down fixtures, one of [function, module, session]")
    parser.addoption("--provisioner", type=str, default='', help="use provisioning service to get hardware to run tests on")
    parser.addoption("--hardware", type=str, default=f'{os.path.expanduser("~")}/.local/hardware.yaml',
                     help="path to hardware_yaml")
    parser.addoption("--extra-tests", action="store", default="",
                     help="tests to run in addition to specified tests and marks. eg. 'test_sanity.py test_extra.py'")


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc):
    """This runs for each test in a row at the beginning but has access only to module.
    At the end of this function I know that if scope is module, initialized_hardware is set.
    The function pytest_collection_modifyitems will handle session/function scope.
    If running unprovisioner: should be a yaml file in $HOME/.local/hardware.yaml which has similar structure to:
    host_name:
        ip: 0.0.0.0
        user: user
        password: pass
        key_file_path: /path/to/pem
    # key_file_path and password are mutually exclusive so use only 1 type of auth
    """
    if hasattr(metafunc.module, '__initialized_hardware'):
        # hardware was initialized already, no need to initialize again.
        return
    fixture_scope = determine_scope(None, metafunc.config)
    if fixture_scope != 'module':
        return

    provisioner = metafunc.config.getoption("--provisioner")
    if provisioner:
        return

    logging.debug("initializing module hardware config to local")
    local_config = get_local_config(metafunc.config.getoption("--hardware"))
    metafunc.module.__initialized_hardware = dict()
    metafunc.module.__initialized_hardware['machines'] = local_config


def get_local_config(local_config_path):
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    logging.debug(f"local_config: {local_config}")
    return local_config


def pytest_sessionstart(session):
    infra_logger.debug("\n<--------------------sesssionstart------------------------>\n")
    scope = determine_scope(None, session.config)
    if scope == 'session':
        if not session.config.getoption("--provisioner"):
            local_hw = get_local_config(session.config.getoption("--hardware"))
            session.__initialized_hardware = dict()
            session.__initialized_hardware['machines'] = local_hw
        else:  # provisioned:
            # I cant init provisioned hardware even if its 'session' scoped because I dont have requirements yet....
            pass


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    infra_logger.debug("\n<-------------------session finish-------------------->\n")
    infra_logger.debug("Sending kill heartbeat")
    session.kill_heartbeat = True
    provisioner = session.config.getoption("--provisioner")
    if provisioner and determine_scope(None, session.config) == 'session':
        provisioner_client.ProvisionerClient(provisioner).release(session.__initialized_hardware['allocation_id'])


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """
    Here I get access to the session for the first time so I can init session_hardware if required.
    I also have access to items (tests) so I can init them if the scope is 'function'.
    'module' scope was initialized in function pytest_generate_tests already.
    At the end of this function, hardware has been initialized for all cases of provisioning and fixture-scope.
    """

    # Add markers on the fly for extra tests
    extra_tests = config.getoption("--extra-tests").split(",")
    for item in items:
        if item.parent.name in extra_tests:
            item.add_marker(pytest.mark.extra)


def determine_scope(fixture_name, config):
    received_scope = config.getoption("--fixture-scope")
    if config.getoption("--provisioner"):
        scope = received_scope if received_scope != 'auto' else 'function'
        return scope
    # If not provisioner it means were running locally in which case no sense re-initializing fixture each test.
    else:
        scope = received_scope if received_scope != 'auto' else 'session'
        return scope


def configured_hardware(request):
    return getattr(request.session, "__initialized_hardware", None) \
           or getattr(request.module, "__initialized_hardware", None) \
           or getattr(request.function, "__initialized_hardware", None)


def init_hosts(hardware, base):
    for machine_name, args in hardware['machines'].items():
        base.hosts[machine_name] = Host(**args)


def kill_heartbeat_thread(hardware, request):
    infra_logger.debug(f"Setting kill_heartbeat on hw {hardware} to True")
    request.session.kill_heartbeat = True


def init_base_config(hardware):
    base = DefaultMunch(Munch)
    base.hosts = Munch()
    init_hosts(hardware, base)
    helpers.init_proxy_containers_and_connect(base.hosts.items())
    return base


@pytest.fixture(scope=determine_scope)
def base_config(request):
    infra_logger.debug("\n<---------------------initing base_config fixture------------------>\n")
    hardware = configured_hardware(request)
    assert hardware, "Didnt find configured_hardware in base_config fixture..."
    base = init_base_config(hardware)
    logging.debug("\n<-----------------sucessfully initialized base_config fixture------------>\n")
    return base


def init_cluster_structure(base_config, cluster_config):
    if cluster_config is None:
        return
    base_config.clusters = Munch.fromDict(cluster_config)
    for cluster in base_config.clusters.values():
        for key, val_list in cluster.items():
            try:
                cluster[key] = Munch()
                for host_name in val_list:
                    cluster[key][host_name] = base_config.hosts[host_name]
            except (KeyError, TypeError):
                cluster[key] = val_list


def match_base_config_hosts_with_hwreqs(hardware_reqs, base_config):
    if len(hardware_reqs) > len(base_config.hosts):
        raise Exception(f"Expected {len(hardware_reqs)} but only {len(base_config.hosts)} allocated")
    for key in hardware_reqs.keys():
        if key in base_config.hosts:
            base_config.hosts[key].alias = key
            continue
        else:
            bc_host_keys = list(base_config.hosts.keys())
            for host in bc_host_keys:
                if host in hardware_reqs:
                    continue
                else:
                    base_config.hosts[key] = base_config.hosts.pop(host)
                    base_config.hosts[key].alias = key
                    break
        assert key in base_config.hosts
    return base_config


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_setup(item):
    infra_logger.debug(f"\n<---------runtest_setup {'.'.join(item.listnames()[-2:])}---------------->\n")
    configured_hw = configured_hardware(item._request)
    if not configured_hw:
        provisioner = item._request.config.getoption("--provisioner")
        if not provisioner:
            hardware = dict()
            hardware['machines'] = get_local_config(item.config.getoption("--hardware"))
        else:
            hardware = provisioner_client.ProvisionerClient(provisioner).provision(item.function.__hardware_reqs)
            item._request.session.kill_heartbeat = lambda: False
            hb = heartbeat_client.HeartbeatClient(item._request.session.kill_heartbeat)
            hb.send_heartbeats_on_thread(hardware['allocation_id'])
            if determine_scope(None, item.config) == 'session':
                infra_logger.warning("running provisioned with session scoped fixture.. Could lead to unexpected results..")
                item.session.__initialized_hardware = dict()
                item.session.__initialized_hardware = hardware

        item.function.__initialized_hardware = hardware

    hardware = configured_hardware(item._request)
    assert hardware, "Couldnt find configured hardware in pytest_runtest_setup"
    outcome = yield  # This will now go to base_config fixture function
    try:
        outcome.get_result()
    except Exception as e:
        try:
            base_config = item._request.getfixturevalue('base_config')
            item.funcargs['base_config'] = base_config
        except FixtureLookupError as fe:
            # We got an exception trying to init base_config fixture
            infra_logger.error("error trying to init base_config fixture")
        # We got an exception trying to init some other fixture, so base_config is available
        raise e
    base_config = item.funcargs['base_config']
    reqs = item.function.__hardware_reqs
    item.funcargs['base_config'] = match_base_config_hosts_with_hwreqs(reqs, base_config)
    hosts = base_config.hosts.items()
    for name, host in hosts:
        logging.info(f"\n\n{host.SshDirect.ssh_string} # host \n{host.SSH.ssh_string} # container\n\n")
    logging.debug("cleaning between tests..")
    initializer.clean_infra_between_tests(hosts)
    init_cluster_structure(base_config, item.function.__cluster_config)
    infra_logger.debug("done runtest_setup")
    infra_logger.debug("\n-----------------runtest call---------------\n")


def pytest_logger_fileloggers(item):
    return [('', logging.INFO), ('infra', logging.DEBUG)]


def pytest_logger_logsdir(config):
    return config.option.logger_logsdir


def pytest_logger_config(logger_config):
    logger_config.split_by_outcome()
    logger_config.set_formatter_class(InfraFormatter)


def pytest_configure(config):
    log_fmt = '%(asctime)s.%(msecs)0.3d %(threadName)-10.10s %(levelname)-6.6s %(message)s %(funcName)-15.15s %(pathname)s:%(lineno)d'
    date_fmt = '%Y-%m-%d %H:%M:%S'

    config.option.showcapture = 'no'
    log_dir = datetime.now().strftime('%Y_%m_%d__%H%M%S')
    logs_dir = os.path.join(os.getcwd(), f'logs/{log_dir}')
    os.makedirs(logs_dir, exist_ok=True)
    config.option.logger_logsdir = logs_dir
    config.option.log_cli_format = log_fmt
    config.option.log_format = log_fmt
    config.option.log_cli_date_format = date_fmt
    config.option.log_file_date_format = date_fmt
    logging.FileHandler.setLevel(logging.getLogger(), level=logging.INFO)
    logging.StreamHandler.setLevel(logging.getLogger(), level=logging.INFO)


def pytest_report_teststatus(report, config):
    logging.debug(report.longreprtext)

def download_host_logs(host, logs_dir):
    dest_dir = os.path.join(logs_dir, host.alias)
    logging.debug(f"remote log folders and permissions: {host.SshDirect.execute('ls /storage/logs -lh || mkdir -p /storage/logs')}")
    host.SshDirect.execute('docker logs automation_proxy &> /tmp/automation_proxy.log')
    remote_log_folders = host.SshDirect.execute('ls /storage/logs').split()
    paths_to_download = [*[f"/storage/logs/{folder}" for folder in remote_log_folders], '/var/log/journal', '/tmp/automation_proxy.log']
    logging.debug(f"Downloading logs from {host.alias} to {dest_dir}. Paths to download: {paths_to_download}")
    os.makedirs(dest_dir, exist_ok=True)
    host.SshDirect.download(re.escape(dest_dir), *paths_to_download)
    logging.debug(f"downloaded log folders: {os.listdir(dest_dir)}")


def _sanitize_nodeid(filename):
    filename = filename.replace('::()::', '/')
    filename = filename.replace('::', '/')
    filename = re.sub(r'\[(.+)\]', r'-\1', filename)
    return filename


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    if result.when == 'call':
        infra_logger.info(f"\n>>>>>>>>>>{'.'.join(item.listnames()[-2:])} {'PASSED' if result.passed else 'FAILED'} {f' -> {call.excinfo.value}' if not result.passed else ''}")

def pytest_runtest_teardown(item):
    infra_logger.debug(f"\n<--------------runtest teardown of {'.'.join(item.listnames()[-2:])}------------------->\n")
    base_config = item.funcargs.get('base_config')
    if not base_config:
        logging.error("base_config fixture wasnt initted properly, cant download logs")
        return
    hosts_to_download = list()
    for host in base_config.hosts.values():
        if not is_k8s(host.SshDirect):
            hosts_to_download.append(host)
    if hosts_to_download:
        try:
            logs_dir = os.path.join(item.config.option.logger_logsdir, _sanitize_nodeid(item.nodeid))
            infra_logger.debug("concurrently downloading logs from hosts...")
            concurrently.run({host.ip: (download_host_logs, host, logs_dir)
                              for host in hosts_to_download})
        except subprocess.CalledProcessError:
            logging.exception("was unable to download logs from a host")

    helpers.tear_down_proxy_containers(base_config.hosts.items())
    scope = determine_scope(None, item.config)
    if scope == 'function':
        provisioner = item._request.config.getoption("--provisioner")
        if provisioner:
            item._request.session.kill_heartbeat = True
            provisioner_client.ProvisionerClient(provisioner).release(item.function.__initialized_hardware['allocation_id'])


def get_log_dir(config):
    handlers = logging.RootLogger.root.handlers
    for handler in handlers:
        if type(handler) == logging.FileHandler:
            path = handler.baseFilename
            return os.path.dirname(path)
    return config.option.logger_logsdir


