import json
import os
import logging
import re
import subprocess
import signal

import pytest
import yaml
from _pytest.fixtures import FixtureLookupError
from munch import *

from automation_infra.utils import initializer, concurrently
from infra.model.host import Host
from pytest_automation_infra import helpers


def pytest_addoption(parser):
    parser.addoption("--fixture-scope", type=str, default='session', choices={"function", "module", "session"},
                     help="every how often to setup/tear down fixtures, one of [function, module, session]")
    parser.addoption("--hardware", type=str, default=f'{os.path.expanduser("~")}/.local/hardware.yaml',
                     help="path to hardware_yaml")
    parser.addoption("--extra-tests", action="store", default="",
                     help="tests to run in addition to specified tests and marks. eg. 'test_sanity.py test_extra.py'")
    parser.addoption("--provisioned-hardware", type=str)


def pytest_addhooks(pluginmanager):
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


def get_local_config(local_config_path):
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    return local_config


def handle_timeout(signum, frame):
    raise TimeoutError("Test has reached timeout threshold, therefore starting teardown")


def pytest_sessionstart(session):
    logging.debug("\n<--------------------sesssionstart------------------------>\n")
    signal.signal(signal.SIGALRM, handle_timeout)
    if session.config.getoption("--provisioned-hardware"):
        session.__initialized_hardware = json.loads(session.config.getoption("--provisioned-hardware"))


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


def configured_hardware(request):
    return getattr(request.session, "__initialized_hardware", None) \
           or getattr(request.function, "__initialized_hardware", None)


def init_hosts(hardware, base):
    for machine_name, args in hardware['machines'].items():
        base.hosts[machine_name] = Host(**args)


def init_base_config(hardware):
    base = DefaultMunch(Munch)
    base.hosts = Munch()
    init_hosts(hardware, base)
    for host in base.hosts.values():
        if host.pkey:
            host.add_to_ssh_agent()
    for name, host in base.hosts.items():
        logging.info(f"[{host}] waiting for ssh connection...")
        host.SshDirect.connect(timeout=60)
        host.SshDirect.execute("mkdir -p -m 777 /tmp/automation_infra")
        logging.info(f"[{host}] success!")
    return base


@pytest.fixture()
def base_config(request):
    logging.debug("\n<---------------------initing base_config fixture------------------>\n")
    hardware = configured_hardware(request)
    assert hardware, "Didnt find configured_hardware in base_config fixture..."
    base = init_base_config(hardware)
    logging.debug("\n<-----------------sucessfully initialized base_config fixture------------>\n")
    # Deploy proxy container (if pytest_devops_infra is invoked)
    request.config.hook.pytest_after_base_config(base_config=base, request=request)
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
    logging.debug(f"\n<---------runtest_setup {'.'.join(item.listnames()[-2:])}---------------->\n")
    configured_hw = configured_hardware(item._request)
    if not configured_hw:
        hardware = dict()
        hardware['machines'] = get_local_config(item.config.getoption("--hardware"))
        item.session.__initialized_hardware = hardware

    hardware = configured_hardware(item._request)
    assert hardware, "Couldnt find configured hardware in pytest_runtest_setup"
    first_machine = next(iter(hardware['machines'].values()))
    hut_conn_format = "HUT connection string:\n\n{}\n\n"
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
    initializer.clean_infra_between_tests(hosts, item, item.config.hook.pytest_clean_between_tests)
    # init_cluster_structure(base_config, item.function.__cluster_config)
    logging.debug("done runtest_setup")
    logging.debug("\n-----------------runtest call---------------\n")


def organize_remote_logs(ssh_direct):
    ssh_direct.execute('sudo sh -c "journalctl > /tmp/journal.log"')


def download_host_logs(host, logs_dir, download_logs_hook=None):
    dest_dir = os.path.join(logs_dir, host.alias)
    os.makedirs(dest_dir, exist_ok=True)
    host.SshDirect.execute('sudo sh -c "journalctl > /tmp/journal.log"')
    host.SshDirect.download(dest_dir, '/tmp/journal.log')
    if download_logs_hook:
        download_logs_hook(host=host, dest_dir=dest_dir)


def pytest_runtest_teardown(item):
    logging.debug(f"\n<--------------runtest teardown of {'.'.join(item.listnames()[-2:])}------------------->\n")
    base_config = item.funcargs.get('base_config')
    if not base_config:
        logging.error("base_config fixture wasnt initted properly, cant download logs")
        return
    try:
        logs_dir = item.config.getoption("--logs-dir")
        logging.debug("concurrently downloading logs from hosts...")
        concurrently.run({host.ip: (download_host_logs, host, logs_dir, item.config.hook.pytest_download_logs)
                          for host in base_config.hosts.values()})
    except subprocess.CalledProcessError:
        logging.exception("was unable to download logs from a host")
    item.config.hook.pytest_after_test(item=item, base_config=base_config)
