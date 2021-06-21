import pathlib
from datetime import datetime
import json
import os
import logging
import re
import subprocess
import signal

import gossip
import pytest
import yaml
from _pytest.fixtures import FixtureLookupError
from munch import *

from automation_infra.utils import concurrently
from infra.model.cluster import Cluster
from infra.model.host import Host
from pytest_automation_infra import helpers

TMP_DIR = "/tmp/habertest"

def pytest_addoption(parser):
    group = parser.getgroup("pytest_automation_infra")
    group.addoption("--fixture-scope", type=str, default='session', choices={"function", "module", "session"},
                     help="every how often to setup/tear down fixtures, one of [function, module, session]")
    group.addoption("--hardware", type=str, default=f'{os.path.expanduser("~")}/.local/hardware.yaml',
                     help="path to hardware_yaml")
    group.addoption("--extra-tests", action="store", default="",
                     help="tests to run in addition to specified tests and marks. eg. 'test_sanity.py test_extra.py'")
    group.addoption("--provisioned-hardware", type=str)
    group.addoption("--install", action="store_true")


def pytest_addhooks(pluginmanager):
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


def get_local_config(local_config_path):
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    return local_config


def pytest_sessionstart(session):
    logging.debug("\n<--------------------sesssionstart------------------------>\n")
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
        if 'alias' not in args:
            args['alias'] = machine_name
        base.hosts[machine_name] = Host(**args)


def init_base_config(hardware):
    base = DefaultMunch(Munch)
    base.hosts = Munch()
    init_hosts(hardware, base)
    # TODO in future: remove init_ssh_direct to support hosts of type aicamera who dont have ssh...
    #   It should happen in some "installer"
    init_ssh_direct(base)
    return base


def init_ssh_direct(base_config):
    for name, host in base_config.hosts.items():
        init_host_ssh_direct(host)


def init_host_ssh_direct(host):
    if host.pkey:
        host.add_to_ssh_agent()
    logging.info(f"[{host}] waiting for ssh connection...")
    host.SshDirect.connect(timeout=60)
    host.SshDirect.execute("mkdir -p -m 777 /tmp/automation_infra")
    logging.info(f"[{host}] success!")


@pytest.fixture()
def base_config(request):
    logging.debug("\n<---------------------initing base_config fixture------------------>\n")
    hardware = configured_hardware(request)
    assert hardware, "Didnt find configured_hardware in base_config fixture..."
    base = init_base_config(hardware)

    test_requirements = request.function.__hardware_reqs
    logging.debug(f"Match base config with {test_requirements}")
    base = match_base_config_hosts_with_hwreqs(test_requirements, base)
    init_cluster_structure(base, request.session.items[0].function.__cluster_config)
    logging.debug("\n<-----------------sucessfully initialized base_config fixture------------>\n")
    if beginning_of_session(request):
        mark_session(request)
        request.config.hook.pytest_after_base_config(base_config=base, request=request)
        _trigger_stage_hooks(base, request, "session")
        if request.config.option.install:
            _trigger_stage_hooks(base, request, "session_install")
    return base


def cluster_installers(base_config, request):
    grouping = request.session.items[0].function.__cluster_config
    if grouping is None:
        return
    for name, cluster in grouping.items():
        installer_type = cluster.get("installer", None) or getattr(request.module, "cluster_installer", None)
        cluster = base_config.clusters[name]
        if installer_type:
            yield cluster, installer_type


def host_installers(base_config, request):
    hardware_reqs = request.session.items[0].function.__hardware_reqs
    for name, req in hardware_reqs.items():
        host = base_config.hosts[name]
        installer_type = req.get("installer", None) or getattr(request.module, "installer", None)
        if installer_type:
            yield host, installer_type


def _trigger_stage_hooks(base_config, request, stage):
    for cluster, installer_type in cluster_installers(base_config, request):
        gossip.trigger_with_tags(stage, kwargs=dict(cluster=cluster, request=request), tags=[installer_type])

    for host, installer_type in host_installers(base_config, request):
        gossip.trigger_with_tags(stage, kwargs=dict(host=host, request=request), tags=[installer_type])

    gossip.trigger_with_tags(stage, kwargs=dict(base_config=base_config, request=request), tags=['base_config'])


def beginning_of_session(request):
    return not os.path.exists(f"{TMP_DIR}/{request.session.id}/{os.path.basename(__file__)}")


def mark_session(request):
    base_dir = f"{TMP_DIR}/{request.session.id}"
    pathlib.Path(base_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(f"{base_dir}/{os.path.basename(__file__)}").touch()


def init_cluster_structure(base_config, cluster_config):
    """
    cluster_config is something like:
    {"cluster1": {"hosts": ["host1", "host2"]}, "cluster2": {"hosts": ["host3"]}}

    And I want to end up with the ability to use syntax like:
    base_config.clusters.cluster1, where cluster1 is a Cluster object.
    base_config.clusters.cluster1.Kubectl.pods()
    or:
    base_config.clusters.cluster1.hosts.host1.SshDirect.execute('ls /')

    This function sets up the base_config.clusters Munch with Cluster objects.
    """
    base_config.clusters = Munch()
    if cluster_config is None:
        return
    for cluster_name, config in cluster_config.items():
        hostnames = config['hosts']
        hosts_dict = dict()
        for hostname in hostnames:
            host = base_config.hosts[hostname]
            hosts_dict[hostname] = host
        base_config.clusters[cluster_name] = Cluster(hosts_dict)


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
    gossip.trigger("runtest_setup")
    configured_hw = configured_hardware(item._request)
    if not configured_hw:
        hardware = dict()
        hardware['machines'] = get_local_config(item.config.getoption("--hardware"))
        item.session.__initialized_hardware = hardware

    hardware = configured_hardware(item._request)
    assert hardware, "Couldnt find configured hardware in pytest_runtest_setup"
    first_machine = next(iter(hardware['machines'].values()))
    hut_conn_format = "HUT connection string:\n\n{}\n\n"
    if first_machine.get('password', None):
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
    logging.debug("cleaning between tests..")
    init_cluster_structure(base_config, item.function.__cluster_config)
    if base_config.clusters:
        concurrently.run([(cluster.clear_plugins) for _, cluster in base_config.clusters.items()])
    concurrently.run([(host.clear_plugins) for _, host in base_config.hosts.items()])
    _trigger_stage_hooks(base_config, item._request, "setup")
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
    if item._evalxfail.istrue():
        return
    logging.debug(f"\n<--------------runtest teardown of {'.'.join(item.listnames()[-2:])}------------------->\n")
    base_config = item.funcargs.get('base_config')
    if not base_config:
        logging.error("base_config fixture wasnt initted properly, cant download logs")
        return
    _trigger_stage_hooks(base_config, item._request, "teardown")
    try:
        logs_dir = item.config.getoption("--logs-dir", f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}')
        logging.debug("concurrently downloading logs from hosts...")
        concurrently.run({host.ip: (download_host_logs, host, logs_dir, item.config.hook.pytest_download_logs)
                          for host in base_config.hosts.values()})
    except subprocess.CalledProcessError:
        logging.exception("was unable to download logs from a host")
    item.config.hook.pytest_after_test(item=item, base_config=base_config)
