import os
import pytest
import yaml
from munch import DefaultFactoryMunch

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from runner import helpers


def pytest_collection_modifyitems(session, config, items):
    """local.yaml should be a yaml file in root of this repo which has similar structure to:
    host:
      ip: 0.0.0.0
      user: user
      password: pass
      key_file_path: '/path/to/pem_file' # key_file_path and password are mutually exclusive, 1 has to be empty string"""
    with open(f'{os.path.dirname(__file__)}/local.yaml', 'r') as f:
        local_config = yaml.full_load(f)
    session.__initialized_hardware = local_config


@pytest.fixture(scope='session')
def base_config(request):
    base = BaseConfig.fromDict(request.session.__initialized_hardware, DefaultFactoryMunch)
    base.host = Host(base.host)
    helpers.init_docker_and_connect(base)
    yield base
    helpers.tear_down_docker(base)
