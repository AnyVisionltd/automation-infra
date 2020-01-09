# -*- coding: utf-8 -*-
import os
import logging
import pytest
import yaml
from munch import *

from infra.model.host import Host
from runner import hardware_initializer, helpers

# TODO: use anylogger


def get_local_config():
    local_config_path = f'{os.path.expanduser("~")}/.local/hardware.yaml'
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    return local_config


def pytest_addoption(parser):
    parser.addoption("--fixture-scope", type=str, default='auto', choices={"function", "module", "session", "auto"},
                     help="every how often to setup/tear down fixtures, one of [function, module, session]")
    parser.addoption("--provisioned", action="store_true", help="use provisioning service to get hardware to run tests on")


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc):
    """This runs for each test in a row at the beginning but has access only to module.
    At the end of this function I know that if scope is module, initialized_hardware is set.
    The function pytest_collection_modifyitems will handle session/function scope.
    If running unprovisioned: should be a yaml file in $HOME/.local/hardware.yaml which has similar structure to:
    host_name:
        ip: 0.0.0.0
        user: user
        password: pass
        key_file_path: /path/to/pem
    # key_file_path and password are mutually exclusive so use only 1 type of auth
    """

    fixture_scope = determine_scope(None, metafunc.config)
    provisioned = metafunc.config.getoption("--provisioned")

    # I only have access to module here (so I cant init 'session' or 'function' scoped hardware):
    if fixture_scope == 'module':
        if provisioned:
            if hasattr(metafunc.module, 'hardware') and not hasattr(metafunc.module, '__initialized_hardware'):
                hardware_config = hardware_initializer.init_hardware(metafunc.module.hardware)
                metafunc.module.__initialized_hardware = hardware_config
            else:
                raise Exception("Module needs to have hardware_reqs set to run with scope module")
        else:
            local_config = get_local_config()
            metafunc.module.__initialized_hardware = local_config


def set_config(tests, config=None):
    for test in tests:
        if config:
            test.function.__initialized_hardware = config
        else:
            assert hasattr(test.function, '__hardware_reqs')
            initialized_hardware = hardware_initializer.init_hardware(test.function.__hardware_reqs)
            test.function.__initialized_hardware = initialized_hardware


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """
    Here I get access to the session for the first time so I can init session_hardware if required.
    I also have access to items (tests) so I can init them if the scope is 'function'.
    'module' scope was initialized in function pytest_generate_tests already.
    At the end of this function, hardware has been initialized for all cases of provisioning and fixture-scope.
    """

    fixture_scope = determine_scope(None, config)
    provisioned = config.getoption("--provisioned")

    if fixture_scope == 'module':
        # This was handled in previous function.
        # In future we may need to init other session params (streaming server, s3, etc) but for now we dont have any.
        return

    if provisioned:
        if fixture_scope == 'function':
            try:
                set_config(items)
            except AssertionError as e:
                raise Exception("there is a test which doesnt have hardware_reqs defined.", e)

        else:  # scope is 'session'
            # This is a strange situation, bc if session scope we shouldnt be running provisioned, or module
            # scope we should have module_hardware defined... Nonetheless to handle this case I think it makes sense
            # to take the hardware_reqs of the first test which has and attach them to the session.
            logging.warning(f"Bypassing erroneous situation where running provisioned but scope is {fixture_scope} "
                            f"defaulting to take hardware req for first test which has reqs defined")
            for test in items:
                if hasattr(test.function, '__hardware_reqs'):
                    hardware_config = hardware_initializer.init_hardware(test.function.__hardware_reqs)
                    session.__initialized_hardware = hardware_config
                    return
            raise Exception("Tried to run provisioned but no collected tests have hardware reqs defined")

    else:  # not provisioned:
        # if running locally I will access the session.__initialized hardware even if initializing fixture per function
        local_config = get_local_config()
        if fixture_scope == 'function':
            set_config(items, local_config)
        else:  # scope is 'session'
            session.__initialized_hardware = local_config




def determine_scope(fixture_name, config):
    received_scope = config.getoption("--fixture-scope")
    if config.getoption("--provisioned"):
        return received_scope if received_scope != 'auto' else 'function'
    # If not provisioned it means were running locally in which case no sense re-initializing fixture each test.
    else:
        return received_scope if received_scope != 'auto' else 'session'


def find_provisioned_hardware(request):
    if hasattr(request.session, '__initialized_hardware'):
        return request.session.__initialized_hardware
    if hasattr(request.module,  '__initialized_hardware'):
        return request.module.__initialized_hardware
    if hasattr(request.function,  '__initialized_hardware'):
        return request.function.__initialized_hardware


@pytest.fixture(scope=determine_scope)
def base_config(request):
    base = BaseConfig.fromDict(request.function.__initialized_hardware, DefaultFactoryMunch)
    base.host = Host(base.host)
    helpers.init_docker_and_connect(base)
    yield base
    helpers.tear_down_docker(base)
