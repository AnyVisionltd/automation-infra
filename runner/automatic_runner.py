import inspect
import importlib
import time
from collections import defaultdict
from pprint import pprint
import pytest
import munch

from runner import hardware_initializer


def run_test_module(module_name, test_name=None):
    module_results = {module_name: {}}
    module = importlib.import_module(f"{module_name}")
    functions = inspect.getmembers(module)
    module_tests = [(k, v) for (k, v) in functions if k.startswith('test')]
    test_names = list()
    for name, test in module_tests:
        if (test_name is None) or (name == test_name):
            test_hardware = test.__hardware_reqs
            print(f"{name} hardware reqs:")
            pprint(test_hardware)
            hardware_config = hardware_initializer.init_hardware(test_hardware)
            print("running pytest...")
            sut_config = f'--sut_config={hardware_config}'
            print(f"sut_config: {sut_config}")
            test_path = '/'.join(module_name.split('.'))
            test_names.append(name)
    res = pytest.main(['-s', *[f"./tests/{test_path}.py::{name}" for name in test_names], '-n 1', sut_config])
    return res
    #return munch.DefaultFactoryMunch.fromDict(module_results, munch.DefaultFactoryMunch)


def sample_module_run():
    all_results = defaultdict(dict)
    module = 'aio_tests.test_aio_demo'
    test = None #  'test_ssh'
    start = time.time()
    test_results = run_test_module(module, test)
    runtime = time.time() - start
    all_results[module] = test_results

    results_munch = munch.DefaultFactoryMunch.fromDict(all_results, munch.DefaultFactoryMunch)

    print('--------ALL TEST RESULTS----------')
    print(f"RUNTIME: {runtime}")
    pprint(results_munch)


if __name__ == '__main__':
    sample_module_run()



