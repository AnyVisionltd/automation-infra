import inspect
import importlib
from collections import defaultdict
from pprint import pprint
import pytest
import munch
import json

from runner import hardware_initializer


def run_test_module(module_name, test_name=None):
    module_results = {module_name: {}}
    module = importlib.import_module(f"{module_name}")
    functions = inspect.getmembers(module)
    module_tests = [(k, v) for (k, v) in functions if k.startswith('test')]
    for name, test in module_tests:
        if (test_name is None) or (name == test_name):
            test_hardware = test.__hardware_reqs
            print(f"{name} hardware reqs:")
            pprint(test_hardware)
            # TODO: I this actually this is where its best to build the base_config
            # rather than parsing this json and sending it in to pytest via cmd params..
            base_config = hardware_initializer.init_hardware(test_hardware)
            print("running pytest...")
            # TODO: here I need to add cmdline params which have to do with initiated hardware (ip address, user/pass, etc)..
            cluster_config = f'--cluster_config={json.dumps(base_config)}'
            print(f"cluster_config: {cluster_config}")
            res = pytest.main(['-s', f"./tests/{module_name}.py::{name}", cluster_config])
            module_results[module_name][name] = res
            #test(base_config.init_base_config_obj())
    return munch.DefaultFactoryMunch.fromDict(module_results, munch.DefaultFactoryMunch)


if __name__ == '__main__':
    # Example run:
    all_results = defaultdict(dict)

    module = 'test_base_config'
    test = 'test_kafka_functionality'
    test_results = run_test_module(module, test)
    all_results[module][test] = test_results

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


