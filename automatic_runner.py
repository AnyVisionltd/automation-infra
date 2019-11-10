import inspect
import importlib
import pprint
import pytest

import hardware_initializer
from infra.model import base_config


def run_test(test_name):
    module = importlib.import_module(f"tests.{test_name}")
    functions = inspect.getmembers(module)
    tests = [(k, v) for (k, v) in functions if k.startswith('test')]
    for name, test in tests:
        test_hardware = test.__hardware_reqs
        print(f"test {name} hardware reqs:")
        pprint.pprint(test_hardware)
        hardware_initializer.init_hardware(test_hardware)
        print("running pytest...")
        pytest.main(['-s', f"./tests/{test_name}.py::{name}"])
        #test(base_config.init_base_config_obj())


if __name__ == '__main__':
    test_name = 'test_decorator'
    run_test(test_name)
