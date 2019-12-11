import os
import inspect
import importlib
import time
from collections import defaultdict
import pprint
import pytest
import munch
import logging

from runner import hardware_initializer
from runner.collector import TestCollector
from runner import helpers

helpers.init_logger()


def collect_tests_and_init_hardware(module_name):
    collector = TestCollector()
    pytest.main(['--collect-only', module_name], plugins=[collector])

    tests = collector.collected
    for test in tests:
        logging.info(f"initing hardware for test {test.nodeid}")
        test.hardware_config = hardware_initializer.init_hardware(test.obj.__hardware_reqs)
    return tests


def run_test_module(module_name):
    # TODO: I dont like how this runs pytest twice. There has got to be a way to collect, init_hardware and then continue
    #  running the already collected tests. look up pytest hooks or somn.
    logging.info("collecting tests and initing hardware..")
    initialized_tests = collect_tests_and_init_hardware(module_name)
    logging.info("done collecting and initing...")
    tests_config = [[f'{os.path.dirname(test.fspath.strpath)}/{os.path.basename(test.nodeid)}', f'--sut_config={test.hardware_config}']
                    for test in initialized_tests]
    pytest_args = ['-s', '-n 1', '--html=report.html', '--self-contained-html']
    for test_config in tests_config:
        pytest_args.extend(test_config)
    logging.info("running tests really...")
    res = pytest.main(pytest_args)
    logging.info("done running tests!")
    return res


def sample_module_run():
    all_results = defaultdict(dict)
    module = 'tests/aio_tests/test_aio_demo.py'
    logging.info(f"running test: {module}")
    start = time.time()
    module_results = run_test_module(module)
    runtime = time.time() - start
    all_results[module] = module_results

    results_munch = munch.DefaultFactoryMunch.fromDict(all_results, munch.DefaultFactoryMunch)
    logging.info('--------TEST RESULTS----------')
    logging.info(pprint.pformat(results_munch))
    logging.info(f"RUNTIME: {runtime}\n\n")


if __name__ == '__main__':
    sample_module_run()



