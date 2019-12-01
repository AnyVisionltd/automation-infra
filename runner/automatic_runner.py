import inspect
import importlib
import time
from collections import defaultdict
from pprint import pprint
import pytest
import munch
import logging

from runner import hardware_initializer

def init_logger():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(relativeCreated)6d %(threadName)s %(message)s',
                        filename='output.log')

init_logger()

def run_test_module(module_name, test_name=None):
    module_results = {module_name: {}}
    module = importlib.import_module(f"{module_name}")
    functions = inspect.getmembers(module)
    module_tests = [(k, v) for (k, v) in functions if k.startswith('test')]
    test_names = list()
    for name, test in module_tests:
        if (test_name is None) or (name == test_name):
            test_hardware = test.__hardware_reqs
            logging.info(f"{name} hardware reqs:")
            pprint(test_hardware)
            hardware_config = hardware_initializer.init_hardware(test_hardware)
            logging.info("running pytest...")
            sut_config = f'--sut_config={hardware_config}'
            logging.info(f"sut_config: {sut_config}")
            test_path = '/'.join(module_name.split('.'))
            test_names.append(name)
    pytest_args = ['-s', *[f"./tests/{test_path}.py::{name}" for name in test_names], '-n 1', sut_config]
    #pytest_args.append('--log-file=output.log')
    res = pytest.main(pytest_args)
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

    logging.info('--------ALL TEST RESULTS----------')
    logging.info(f"RUNTIME: {runtime}")
    pprint(results_munch)


if __name__ == '__main__':
    sample_module_run()



