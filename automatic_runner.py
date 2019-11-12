import inspect
import importlib
from pprint import pprint
import pytest
import munch

import hardware_initializer
from infra.model import base_config



def run_test_module(module_name):
    module_results = {module_name: {}}
    module = importlib.import_module(f"{module_name}")
    functions = inspect.getmembers(module)
    module_tests = [(k, v) for (k, v) in functions if k.startswith('test')]
    for name, test in module_tests:
        test_hardware = test.__hardware_reqs
        print(f"{name} hardware reqs:")
        pprint(test_hardware)
        hardware_initializer.init_hardware(test_hardware)
        print("running pytest...")
        res = pytest.main(['-s', f"./tests/{module_name}.py::{name}"])
        module_results[module_name][name] = res
        #test(base_config.init_base_config_obj())
    return munch.DefaultFactoryMunch.fromDict(module_results, munch.DefaultFactoryMunch)


if __name__ == '__main__':
    # Example run:
    all_results = {}

    test_name = 'test_decorator'
    test_results = run_test_module(test_name)
    print(f"MODULE {test_name} RESULTS:test_host_construction")
    pprint(test_results)
    print()

    all_results[test_name] = test_results

    test_name = 'test_base_config'
    test_results = run_test_module(test_name)
    print(f"MODULE: {test_name} RESULTS:")
    pprint(test_results)
    print()

    all_results[test_name] = test_results
    results_munch = munch.DefaultFactoryMunch.fromDict(all_results, munch.DefaultFactoryMunch)

    print('--------ALL TEST RESULTS----------')
    pprint(results_munch)


