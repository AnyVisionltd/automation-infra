# -*- coding: utf-8 -*-
import os
import logging
import re
import threading
import time
from datetime import datetime

import aiohttp
import pytest
import requests
import yaml
from munch import *

from automation_infra.utils import initializer, concurrently
from infra.model.host import Host
from automation_infra.plugins.ssh import SSH
from automation_infra.plugins.ssh_direct import SshDirect
from pytest_automation_infra import hardware_initializer, helpers
from pytest_automation_infra.helpers import is_k8s
import copy


class InfraFormatter(logging.Formatter):
    def __init__(self):
        msg_fmt = "%(asctime)20.20s.%(msecs)d %(threadName)-10.10s %(levelname)-6.6s %(message)-75s " \
              "%(funcName)-15.15s %(pathname)-70s:%(lineno)4d"
        logging.Formatter.__init__(self, msg_fmt, datefmt='%Y-%m-%d %H:%M:%S')


def get_local_config(local_config_path):
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    logging.debug(f"local_config: {local_config}")
    return local_config


def pytest_addoption(parser):
    parser.addoption("--fixture-scope", type=str, default='auto', choices={"function", "module", "session", "auto"},
                     help="every how often to setup/tear down fixtures, one of [function, module, session]")
    parser.addoption("--provisioner", type=str, help="use provisioning service to get hardware to run tests on")
    parser.addoption("--hardware", type=str, default=f'{os.path.expanduser("~")}/.local/hardware.yaml',
                     help="path to hardware_yaml")


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

    fixture_scope = determine_scope(None, metafunc.config)
    provisioner = metafunc.config.getoption("--provisioner")

    # I only have access to module here (so I cant init 'session' or 'function' scoped hardware):
    if fixture_scope == 'module':
        if provisioner:
            logging.debug("initializing module hardware config to provisioner")
            if hasattr(metafunc.module, 'hardware') and not hasattr(metafunc.module, '__initialized_hardware'):
                hardware_config = hardware_initializer.init_hardware(metafunc.module.hardware, provisioner)
                metafunc.module.__initialized_hardware = hardware_config
            else:
                raise Exception("Module needs to have hardware_reqs set to run with scope module")
        else:
            logging.debug("initializing module hardware config to local")
            local_config = get_local_config(metafunc.config.getoption("--hardware"))
            metafunc.module.__initialized_hardware = local_config


def set_config(tests, config=None, provisioner=None):
    for test in tests:
        if config:
            test.function.__initialized_hardware = config
        else:
            assert hasattr(test.function, '__hardware_reqs')
            initialized_hardware = hardware_initializer.init_hardware(test.function.__hardware_reqs, provisioner)
            test.function.__initialized_hardware = initialized_hardware


def send_heartbeat(provisioned_hw, stop):
    logging.debug(f"Starting heartbeat to provisioned hardware: {provisioned_hw}")
    while True:
        for host in provisioned_hw.values():
            logging.debug(f"host: {host}")
            if "allocation_id" not in host:
                logging.debug("'allocation_id' not in host data")
                continue
            allocation_id = host['allocation_id']
            logging.debug(f"allocation_id: {allocation_id}")
            payload = {"allocation_id": allocation_id}
            logging.debug(f"sending post hb request payload: {payload}")
            response = requests.post(
                "%sapi/heartbeat" % os.getenv('HEARTBEAT_SERVER'), json=payload)
            logging.debug(f"post response {response}")
            if response.status_code != 200:
                logging.error(
                    "Failed to send heartbeat! Got status %s",
                    response.json()
                    )
        if stop():
            logging.debug(f"Killing heartbeat to hw {provisioned_hw}")
            break
        time.sleep(3)
    logging.debug(f"Heartbeat to hardware {provisioned_hw} stopped")


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    pass


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    logging.debug("Sending kill heartbeat")
    session.kill_heartbeat = True


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """
    Here I get access to the session for the first time so I can init session_hardware if required.
    I also have access to items (tests) so I can init them if the scope is 'function'.
    'module' scope was initialized in function pytest_generate_tests already.
    At the end of this function, hardware has been initialized for all cases of provisioning and fixture-scope.
    """

    fixture_scope = determine_scope(None, config)
    provisioner = config.getoption("--provisioner")

    if fixture_scope == 'module':
        # This was handled in previous function.
        # In future we may need to init other session params (streaming server, s3, etc) but for now we dont have any.
        return

    if provisioner:
        if fixture_scope == 'function':
            logging.debug(f"initializing '{fixture_scope}' hardware config to provisioner")
            try:
                set_config(items, provisioner=provisioner)
            except AssertionError as e:
                raise Exception("there is a test which doesnt have hardware_reqs defined.", e)

        else:  # scope is 'session'
            logging.debug(f"initializing '{fixture_scope}' (should be session) hardware config to provisioner")
            # This is a strange situation, bc if session scope we shouldnt be running provisioner, or module
            # scope we should have module_hardware defined... Nonetheless to handle this case I think it makes sense
            # to take the hardware_reqs of the first test which has and attach them to the session.
            logging.warning(f"Bypassing erroneous situation where running provisioner but scope is '{fixture_scope}' "
                            f"defaulting to take hardware req for first test which has reqs defined")
            for test in items:
                if hasattr(test.function, '__hardware_reqs'):
                    hardware_config = hardware_initializer.init_hardware(test.function.__hardware_reqs, provisioner)
                    session.__initialized_hardware = hardware_config
                    return
            raise Exception("Tried to run provisioner but no collected tests have hardware reqs defined")

    else:  # not provisioner:
        # if running locally I will access the session.__initialized hardware even if initializing fixture per function
        local_config = get_local_config(config.getoption("--hardware"))
        if fixture_scope == 'function':
            logging.debug("initializing 'function' hardware config to local_config")
            set_config(items, local_config)
        else:  # scope is 'session'
            logging.debug("initializing 'session' hardware config to local_config")
            session.__initialized_hardware = local_config


def determine_scope(fixture_name, config):
    received_scope = config.getoption("--fixture-scope")
    if config.getoption("--provisioner"):
        scope = received_scope if received_scope != 'auto' else 'function'
        logging.debug(f"scope: {scope} provisioner: True")
        return scope
    # If not provisioner it means were running locally in which case no sense re-initializing fixture each test.
    else:
        scope = received_scope if received_scope != 'auto' else 'session'
        logging.debug(f"scope: {scope} provisioner: False")
        return scope


def find_provisioner_hardware(request):
    if hasattr(request.session, '__initialized_hardware'):
        logging.debug("returning 'session' initialized hardware")
        return request.session.__initialized_hardware
    if hasattr(request.module,  '__initialized_hardware'):
        logging.debug("returning 'module' initialized hardware")
        return request.module.__initialized_hardware
    if hasattr(request.function,  '__initialized_hardware'):
        logging.debug("returning 'function' initialized hardware")
        return request.function.__initialized_hardware


def try_initing_hosts_intelligently(request, hardware, base):
    """This function tries matching initialized hardware with function hardware requirements intelligently. In the
     provisioner case the matching is trivial. In the un-provisioner, the function matches hardware keys with
     available keys, and then assigns the rest of the keys.
     More detailed explanation:
     If provisioner, hardware will hold each and every key in function hardware requirements, and therefore never enter
     the first else (trivial case).
     If running un-provisioner, hardware will hold the contents of the hardware.yaml file, which will have none/some/all
     of the tests requirements (in terms of alias). So what the else does if the function key (required hardware)
     isnt in hardware keys, takes a random key, if it isnt required by the test, matches it to the alias which the
     function requires.
     """
    try:
        for key in request.function.__hardware_reqs.keys():
            if key in base.hosts.keys():
                # already initialized, can happen because of the folllowing 'for' loop
                continue
            # This is the trivial case, the required key exists in the hardware:
            if key in hardware.keys():
                details = hardware[key]
                base.hosts[key] = Host(Munch(details))
            else:
                # This is the 'intelligent' part, trying to match keys from hardware.yaml to test reqs:
                for name, details in hardware.items():
                    if name in request.function.__hardware_reqs.keys():
                        base.hosts[name] = Host(Munch(details))
                    else:
                        base.hosts[key] = Host(Munch(details))
                        break

                base.hosts[key] = Host(Munch(details))

    except AttributeError:
        # This happens when running with module/session scope
        for machine_name in hardware.keys():
            logging.debug(f"Constructing host {machine_name}")
            host_config = Munch(copy.copy(hardware[machine_name]))
            host_config['alias'] = machine_name
            base.hosts[machine_name] = Host(host_config)
    except KeyError as err:
        raise Exception(f"not enough hosts defined in hardware.yaml to run test {request.function}")


def start_heartbeat_thread(hardware, request):
    request.session.kill_heartbeat = False
    hb_thread = threading.Thread(target=send_heartbeat,
                                 args=(hardware, lambda: request.session.kill_heartbeat),
                                 daemon=False)
    hb_thread.start()
    return hb_thread


def kill_heartbeat_thread(hardware, request):
    logging.debug(f"Setting kill_heartbeat on hw {hardware} to True")
    request.session.kill_heartbeat = True


@pytest.fixture(scope=determine_scope)
def base_config(request):
    hardware = find_provisioner_hardware(request)
    provisioned = request.config.getoption("--provisioner")
    if provisioned:
        hb_thread = start_heartbeat_thread(hardware, request)
    base = DefaultMunch(Munch)
    base.hosts = Munch()
    try_initing_hosts_intelligently(request, hardware, base)
    helpers.init_proxy_containers_and_connect(base.hosts.items())
    logging.info("sucessfully initialized base_config fixture")
    yield base
    logging.debug("tearing down base_config fixture")
    helpers.tear_down_proxy_containers(base.hosts.items())
    if provisioned:
        kill_heartbeat_thread(hardware, request)
        hb_thread.join()


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_setup(item):
    # The yield allows the base_config fixture to be init'ed:
    outcome = yield
    outcome.get_result()
    hosts = item.funcargs['base_config'].hosts.items()
    initializer.clean_infra_between_tests(hosts)


def pytest_logger_fileloggers(item):
    logging.FileHandler.setLevel(logging.getLogger(), level=logging.DEBUG)
    return [('')]


def pytest_logger_logsdir(config):
    return config.option.logger_logsdir


def pytest_logger_config(logger_config):
    logger_config.split_by_outcome()
    logger_config.set_formatter_class(InfraFormatter)


def pytest_configure(config):
    log_fmt = '%(asctime)s.%(msecs)0.3d %(threadName)-10.10s %(levelname)-6.6s %(message)s %(funcName)-15.15s %(pathname)s:%(lineno)d'
    date_fmt = '%Y-%m-%d %H:%M:%S'

    config.option.showcapture = 'no'
    log_dir = datetime.now().strftime('%Y_%m_%d:%H:%M:%S')
    config.option.logger_logsdir = os.path.join(os.path.dirname(__file__), f'../logs/{log_dir}')
    config.option.log_cli = True
    config.option.log_cli_level = 'INFO'
    config.option.log_cli_format = log_fmt
    config.option.log_format = log_fmt
    config.option.log_cli_date_format = date_fmt
    config.option.log_file_date_format = date_fmt


def pytest_report_teststatus(report, config):
    logging.debug(report.longreprtext)

def download_host_logs(host, logs_dir):
    dest_dir = os.path.join(logs_dir, host.alias)
    paths_to_download = ['/storage/logs/', '/var/log/journal']
    logging.info(f"Downloading logs from {host.alias}")
    os.system(f"mkdir -p {dest_dir}")
    host.SshDirect.download(re.escape(dest_dir), *paths_to_download)


def pytest_runtest_teardown(item):
    base_config = item.funcargs['base_config']
    if is_k8s(base_config.hosts.host.SshDirect):
        # TODO: implement download_logs for k8s
        return
    hosts = item.funcargs['base_config'].hosts.values()
    concurrently.run({host.ip: (download_host_logs, host, get_log_dir(item.config))
                      for host in hosts})


def get_log_dir(config):
    handlers = logging.RootLogger.root.handlers
    for handler in handlers:
        if type(handler) == logging.FileHandler:
            path = handler.baseFilename
            return os.path.dirname(path)
    return config.option.logger_logsdir
