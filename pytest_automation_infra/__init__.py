# -*- coding: utf-8 -*-
import os
import logging
import pytest
import yaml
from munch import *

from infra.model.host import Host
from pytest_automation_infra import hardware_initializer, helpers


def get_local_config():
    local_config_path = f'{os.path.expanduser("~")}/.local/hardware.yaml'
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    logging.info(f"local_config: {local_config}")
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
            logging.info("initializing module hardware config to provisioned")
            if hasattr(metafunc.module, 'hardware') and not hasattr(metafunc.module, '__initialized_hardware'):
                hardware_config = hardware_initializer.init_hardware(metafunc.module.hardware)
                metafunc.module.__initialized_hardware = hardware_config
            else:
                raise Exception("Module needs to have hardware_reqs set to run with scope module")
        else:
            logging.info("initializing module hardware config to local")
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
            logging.info(f"initializing '{fixture_scope}' hardware config to provisioned")
            try:
                set_config(items)
            except AssertionError as e:
                raise Exception("there is a test which doesnt have hardware_reqs defined.", e)

        else:  # scope is 'session'
            logging.info(f"initializing '{fixture_scope}' (should be session) hardware config to provisioned")
            # This is a strange situation, bc if session scope we shouldnt be running provisioned, or module
            # scope we should have module_hardware defined... Nonetheless to handle this case I think it makes sense
            # to take the hardware_reqs of the first test which has and attach them to the session.
            logging.warning(f"Bypassing erroneous situation where running provisioned but scope is '{fixture_scope}' "
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
            logging.info("initializing 'function' hardware config to local_config")
            set_config(items, local_config)
        else:  # scope is 'session'
            logging.info("initializing 'session' hardware config to local_config")
            session.__initialized_hardware = local_config


def determine_scope(fixture_name, config):
    received_scope = config.getoption("--fixture-scope")
    if config.getoption("--provisioned"):
        scope = received_scope if received_scope != 'auto' else 'function'
        logging.info(f"scope: {scope} provisioned: True")
        return scope
    # If not provisioned it means were running locally in which case no sense re-initializing fixture each test.
    else:
        scope = received_scope if received_scope != 'auto' else 'session'
        logging.info(f"scope: {scope} provisioned: False")
        return scope


def find_provisioned_hardware(request):
    if hasattr(request.session, '__initialized_hardware'):
        logging.info("returning 'session' initialized hardware")
        return request.session.__initialized_hardware
    if hasattr(request.module,  '__initialized_hardware'):
        logging.info("returning 'module' initialized hardware")
        return request.module.__initialized_hardware
    if hasattr(request.function,  '__initialized_hardware'):
        logging.info("returning 'function' initialized hardware")
        return request.function.__initialized_hardware


def try_initing_hosts_intelligently(request, hardware, base):
    """This function tries matching initialized hardware with function hardware requirements intelligently. In the
     provisioned case the matching is trivial. In the un-provisioned, the function matches hardware keys with
     available keys, and then assigns the rest of the keys.
     More detailed explanation:
     If provisioned, hardware will hold each and every key in function hardware requirements, and therefore never enter
     the first else (trivial case).
     If running un-provisioned, hardware will hold the contents of the hardware.yaml file, which will have none/some/all
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
            logging.info(f"Constructing host {machine_name}")
            base.hosts[machine_name] = Host(Munch(hardware[machine_name]))
    except KeyError:
        raise Exception(f"not enough hosts defined in hardware.yaml to run test {request.function}")


@pytest.fixture(scope=determine_scope)
def base_config(request):
    hardware = find_provisioned_hardware(request)
    base = DefaultMunch(Munch)
    base.hosts = Munch()
    try_initing_hosts_intelligently(request, hardware, base)
    helpers.init_dockers_and_connect(base.hosts.items())
    logging.info("sucessfully initialized base_config fixture. Running test...")
    yield base
    logging.info("tearing down base_config fixture")
    helpers.tear_down_dockers(base.hosts.items())


