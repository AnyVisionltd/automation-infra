# -*- coding: utf-8 -*-
import os
import logging
import re
import socket
import subprocess
import sys
import threading
import time
import signal
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
from infra.utils import ssh_agent
from pytest_automation_infra import provisioner_client, helpers, heartbeat_client
from pytest_automation_infra.helpers import is_k8s


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
    parser.addoption("--logs-dir", action="store", default="", help="custom directory to store logs in")

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


def handle_timeout(signum, frame):
    raise TimeoutError("Test has reached timeout threshold, therefore starting teardown")


def pytest_sessionstart(session):
    logging.debug("\n<--------------------sesssionstart------------------------>\n")
    signal.signal(signal.SIGALRM, handle_timeout)
    scope = determine_scope(None, session.config)
    session.kill_heartbeat = threading.Event()
    ssh_agent.setup_agent()
    if scope == 'session':
        if not session.config.getoption("--provisioner"):
            local_hw = get_local_config(session.config.getoption("--hardware"))
            session.__initialized_hardware = dict()
            session.__initialized_hardware['machines'] = local_hw
        else:  # provisioned:
            provisioner = session.config.getoption("--provisioner")
            cert = os.getenv('HABERTEST_SSL_CERT', None)
            key = os.getenv('HABERTEST_SSL_KEY', None)
            session.provisioner = provisioner_client.ProvisionerClient(provisioner, cert, key)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    logging.debug("\n<-------------------session finish-------------------->\n")
    if not session.kill_heartbeat:
        return
    logging.debug("Sending kill heartbeat")
    session.kill_heartbeat.set()
    provisioner = session.config.getoption("--provisioner")
    if provisioner and determine_scope(None, session.config) == 'session':
        session.provisioner.release(session.__initialized_hardware['allocation_id'])


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
    logging.debug(f"Setting kill_heartbeat on hw {hardware} to True")
    request.session.kill_heartbeat.set()


def init_base_config(hardware):
    base = DefaultMunch(Munch)
    base.hosts = Munch()
    init_hosts(hardware, base)
    for host in base.hosts.values():
        if host.pkey:
            host.add_to_ssh_agent()
    helpers.init_proxy_containers_and_connect(base.hosts.items())
    return base


@pytest.fixture(scope=determine_scope)
def base_config(request):
    logging.debug("\n<---------------------initing base_config fixture------------------>\n")
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
    configure_item_loghandler(item)
    logging.debug(f"\n<---------runtest_setup {'.'.join(item.listnames()[-2:])}---------------->\n")
    configured_hw = configured_hardware(item._request)
    if not configured_hw:
        provisioner = item._request.config.getoption("--provisioner")
        if not provisioner:
            hardware = dict()
            hardware['machines'] = get_local_config(item.config.getoption("--hardware"))
        else:
            hardware = item.session.provisioner.provision(item.function.__hardware_reqs)
            item._request.session.kill_heartbeat = threading.Event()
            hb = heartbeat_client.HeartbeatClient(item._request.session.kill_heartbeat,
                                                  ep=os.getenv('HABERTEST_HEARTBEAT_SERVER', "http://localhost:7080"),
                                                  cert=os.getenv('HABERTEST_SSL_CERT', None),
                                                  key=os.getenv('HABERTEST_SSL_KEY', None))
            hb.send_heartbeats_on_thread(hardware['allocation_id'])
            if determine_scope(None, item.config) == 'session':
                item.session.__initialized_hardware = dict()
                item.session.__initialized_hardware = hardware

        item.function.__initialized_hardware = hardware

    hardware = configured_hardware(item._request)
    assert hardware, "Couldnt find configured hardware in pytest_runtest_setup"
    first_machine = next(iter(hardware['machines'].values()))
    hut_conn_format = "HUT connection string:\n\n {} \n\n"
    if first_machine['password']:
        conn_string = f"sshpass -p {next(iter(hardware['machines'].values()))['password']} ssh -o StrictHostKeyChecking=no {next(iter(hardware['machines'].values()))['user']}@{next(iter(hardware['machines'].values()))['ip']}"
    else:
        conn_string = f"ssh -i {os.path.expanduser('~')}/.ssh/anyvision-devops.pem {first_machine['user']}@{first_machine['ip']}"
    logging.info(hut_conn_format.format(conn_string))
    outcome = yield  # This will now go to base_config fixture function
    try:
        outcome.get_result()
    except Exception as e:
        try:
            base_config = item._request.getfixturevalue('base_config')
            item.funcargs['base_config'] = base_config
        except FixtureLookupError as fe:
            # We got an exception trying to init base_config fixture
            logging.error("error trying to init base_config fixture")
        # We got an exception trying to init some other fixture, so base_config is available
        raise e
    base_config = item.funcargs['base_config']
    reqs = item.function.__hardware_reqs
    item.funcargs['base_config'] = match_base_config_hosts_with_hwreqs(reqs, base_config)
    hosts = base_config.hosts.items()
    logging.debug("cleaning between tests..")
    initializer.clean_infra_between_tests(hosts, item.function.__name__)
    init_cluster_structure(base_config, item.function.__cluster_config)
    logging.debug("done runtest_setup")
    logging.debug("\n-----------------runtest call---------------\n")


def pytest_logger_fileloggers(item):
    return [('', logging.INFO)]


def configure_item_loghandler(item):
    config = item.config
    log_dir = os.path.join(config.option.logger_logsdir, _sanitize_nodeid(item.nodeid))
    os.environ["TEST_LOG_DIR"] = log_dir
    os.makedirs(log_dir, exist_ok=True)
    debug_fh = logging.FileHandler(f'{log_dir}/infra.log', mode='w')
    debug_fh.setLevel(logging.DEBUG)
    debug_fh.setFormatter(logging.Formatter(config.option.log_format))
    item.log_handler = debug_fh
    logging.getLogger().addHandler(item.log_handler)


def pytest_logger_logsdir(config):
    return config.option.logger_logsdir


def pytest_logger_config(logger_config):
    logger_config.split_by_outcome()
    logger_config.set_formatter_class(InfraFormatter)


def configure_logging(config):
    config.option.log_format = '%(asctime)s.%(msecs)0.3d %(threadName)-10.10s %(levelname)-6.6s %(message)s %(funcName)-15.15s %(pathname)s:%(lineno)d'
    config.option.log_cli_format = config.option.log_format

    config.option.log_file_date_format = '%Y-%m-%d %H:%M:%S'
    config.option.log_cli_date_format = config.option.log_file_date_format
    custom_logs_dir = config.getoption("--logs-dir")
    session_logs_dir = custom_logs_dir if custom_logs_dir else f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}'

    infra_logs_dir = f'{session_logs_dir}/infra_logs'
    os.makedirs(infra_logs_dir, exist_ok=True)

    # tests_logs_dir = os.path.join(os.getcwd(), f'{session_logs_dir}/test_logs')
    tests_logs_dir = f'{session_logs_dir}/tests_logs'
    os.makedirs(tests_logs_dir, exist_ok=True)

    config.option.logger_logsdir = tests_logs_dir

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    log_fmt = config.option.log_format

    debug_fh = logging.FileHandler(f'{infra_logs_dir}/debug.log', mode='w')
    debug_fh.setLevel(logging.DEBUG)
    debug_fh.setFormatter(logging.Formatter(log_fmt))
    root_logger.addHandler(debug_fh)

    info_fh = logging.FileHandler(f'{infra_logs_dir}/info.log', mode='w')
    info_fh.setLevel(logging.INFO)
    info_fh.setFormatter(logging.Formatter(log_fmt))
    root_logger.addHandler(info_fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(log_fmt))
    root_logger.addHandler(ch)


def pytest_configure(config):
    configure_logging(config)


def organize_remote_logs(ssh):
    ssh.execute('sudo chmod ugo+rw /tmp/automation_infra')
    ssh.execute('docker logs automation_proxy &> /tmp/automation_proxy.log')
    ssh.execute('sudo mv /tmp/automation_proxy.log /tmp/automation_infra/automation_proxy.log')


def download_host_logs(host, logs_dir):
    dest_dir = os.path.join(logs_dir, host.alias)
    host.SshDirect.execute('docker logs automation_proxy &> /tmp/automation_proxy.log')
    host.SshDirect.execute('sudo sh -c "journalctl > /storage/logs/journal.log"')
    organize_remote_logs(host.SshDirect)
    remote_log_folders = host.SSH.execute('ls /storage/logs').split()
    logging.debug(f"remote log folders: {remote_log_folders}")
    paths_to_download = [*[f"/storage/logs/{folder}" for folder in remote_log_folders], '/tmp/automation_proxy.log']
    logging.debug(f"Downloading logs from {host.alias} to {dest_dir}. Paths to download: {paths_to_download}")
    os.makedirs(dest_dir, exist_ok=True)
    dest_gz = '/tmp/automation_infra/logs.tar.gz'
    host.SSH.compress(paths_to_download, dest_gz)
    host.SSH.download(re.escape(dest_dir), dest_gz)
    logging.debug(f"downloaded log folders: {os.listdir(dest_dir)}")


def _sanitize_nodeid(filename):
    filename = filename.replace('::()::', '/')
    filename = filename.replace('::', '/')
    filename = re.sub(r'\[(.+)\]', r'-\1', filename)
    return filename


def pytest_report_teststatus(report, config):
    if report.longreprtext:
        logging.info(report.longreprtext)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    if result.when == 'call':
        logging.info(f"\n>>>>>>>>>>{'.'.join(item.listnames()[-2:])} {'PASSED' if result.passed else 'FAILED'} {f' -> {call.excinfo.value}' if not result.passed else ''}")


def pytest_runtest_teardown(item):
    logging.debug(f"\n<--------------runtest teardown of {'.'.join(item.listnames()[-2:])}------------------->\n")
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
            logging.debug("concurrently downloading logs from hosts...")
            concurrently.run({host.ip: (download_host_logs, host, logs_dir)
                              for host in hosts_to_download})
        except subprocess.CalledProcessError:
            logging.exception("was unable to download logs from a host")

    helpers.tear_down_proxy_containers(base_config.hosts.items())
    scope = determine_scope(None, item.config)
    if scope == 'function':
        provisioner = item._request.config.getoption("--provisioner")
        if provisioner:
            item._request.session.kill_heartbeat.set()
            item.session.provisioner.release(item.function.__initialized_hardware['allocation_id'])
    logging.getLogger().removeHandler(item.log_handler)


def get_log_dir(config):
    handlers = logging.RootLogger.root.handlers
    for handler in handlers:
        if type(handler) == logging.FileHandler:
            path = handler.baseFilename
            return os.path.dirname(path)
    return config.option.logger_logsdir


