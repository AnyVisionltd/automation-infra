# -*- coding: utf-8 -*-
import os
import json

import pytest
import yaml
from munch import DefaultFactoryMunch

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from runner import hardware_initializer, helpers


def pytest_addoption(parser):
    parser.addoption("--fixture-scope", type=str, default='auto', choices={"function", "module", "session", "auto"},
                     help="every how often to setup/tear down fixtures, one of [function, module, session]")
    parser.addoption("--provisioned", help="use provisioning service to get hardware to run tests on")


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc):
    """This runs for each test in a row at the beginning but has access only to module At the end of this function I
    know that if scope is module, initialized_hardware is mostly set, the only thing left to handle is the case of
    provisioned but module doesnt have hardware_property. I handle that in the next function, the same way I handle
    trying to run provisioned with session scope. The function pytest_collection_modifyitems will handle
    session/function scope, provisioned and not. If running unprovisioned: local.yaml should be a yaml file in root
    of this repo which has similar structure to:
    host:
        ip: 0.0.0.0
        user: user
        password: pass
        key_file_path: '/path/to/pem'
    # key_file_path and password are mutually exclusive, 1 has to be empty string
    """

    fixture_scope = metafunc.config.getoption("--fixture-scope")
    provisioned = metafunc.config.getoption("--provisioned")

    # I only have access to module here (so I cant init session or function scoped hardware):
    if fixture_scope == 'module':
        if provisioned:
            if hasattr(metafunc.module, 'hardware') and not hasattr(metafunc.module, '__initialized_hardware'):
                hardware_config = hardware_initializer.init_hardware(metafunc.module.hardware)
                metafunc.module.__initialized_hardware = json.loads(hardware_config)
            else:
                # This pseudo-flawed case is handled in the next function but really should happen.
                print("WARNING: This is a flawed situation, shouldnt run provisioned with module scope when module"
                      "doesnt have hardware property!")
        else:
            with open(f'{os.path.dirname(__file__)}/local.yaml', 'r') as f:
                local_config = yaml.full_load(f)
            metafunc.module.__initialized_hardware = local_config


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """Here I get access to the session for the first time so I can init session_hardware if required.
    I also have access to items (tests) so I can init them if the scope is 'function'.
    I dont have access to module (was initialized in prev function (pytest_generate_tests) except for flawed case).
    So now I need to handle session or function scope, and the pseudo-flawed situation where provisioned but
    module doesnt define hardware.
    At the end of this function, all cases of provisioning and fixture-scope have been handled.
    """

    fixture_scope = config.getoption("--fixture-scope")
    provisioned = config.getoption("--provisioned")

    if provisioned:
        if fixture_scope == 'function':
            for item in items:
                assert hasattr(item.function, '__hardware_reqs'), "need to set hardware requirements for test"
                hardware_config = hardware_initializer.init_hardware(item.function.__hardware_reqs)
                item.function.__initialized_hardware = json.loads(hardware_config)
        else:
            # This is a pseudo-flawed situation, bc if session scope we shouldnt be running provisioned, or module
            # scope we should have module_hardware defined... Nonetheless to handle this case I think it makes sense
            # to take the hardware_reqs of the first test which has and attach them to the session.
            for item in items:
                if hasattr(item.function, '__hardware_reqs'):
                    hardware_config = hardware_initializer.init_hardware(item.function.__hardware_reqs)
                    # This works for session and module scope because when getting initialized hardware I check first
                    # at the session level and only afterwards at the module level:
                    session.__initialized_hardware = json.loads(hardware_config)
                    break

    else:  # not provisioned:
        # if running locally I will access the session.__initialized hardware even if initializing fixture per function
        with open(f'{os.path.dirname(__file__)}/local.yaml', 'r') as f:
            local_config = yaml.full_load(f)
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
    if hasattr(request.fuction,  '__initialized_hardware'):
        return request.function.__initialized_hardware


@pytest.fixture(scope=determine_scope)
def base_config(request):
    hardware = find_provisioned_hardware(request)
    base = BaseConfig.fromDict(hardware, DefaultFactoryMunch)
    base.host = Host(base.host)
    helpers.init_docker_and_connect(base)
    yield base
    helpers.tear_down_docker(base)
