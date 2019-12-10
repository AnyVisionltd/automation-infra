import os
import inspect
import importlib
import time
from collections import defaultdict
from pprint import pprint
import pytest
import munch
import logging

from runner import hardware_initializer
from runner.collector import TestCollector


def init_logger():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(relativeCreated)6d %(threadName)s %(message)s',
                        filename='output.log')

init_logger()


def collect_tests_and_init_hardware(module_name):
    collector = TestCollector()
    pytest.main(['--collect-only', module_name], plugins=[collector])

    tests = collector.collected
    for test in tests:
        test.hardware_config = hardware_initializer.init_hardware(test.obj.__hardware_reqs)
    return tests


def run_test_module(module_name):
    # TODO: I dont like how this runs pytest twice. There has got to be a way to collect, init_hardware and then continue
    #  running the already collected tests. look up pytest hooks or somn.

    initialized_tests = collect_tests_and_init_hardware(module_name)

    tests_config = [[f'{os.path.dirname(test.fspath.strpath)}/{os.path.basename(test.nodeid)}', f'--sut_config={test.hardware_config}']
                    for test in initialized_tests]
    pytest_args = ['-s', '-n 1', '--html=report.html', '--self-contained-html']
    for test_config in tests_config:
        pytest_args.extend(test_config)
    res = pytest.main(pytest_args)
    return res


def sample_module_run():
    all_results = defaultdict(dict)
    module = 'tests/aio_tests/test_aio_demo.py'
    start = time.time()
    test_results = run_test_module(module)
    runtime = time.time() - start
    all_results[module] = test_results

    results_munch = munch.DefaultFactoryMunch.fromDict(all_results, munch.DefaultFactoryMunch)

    logging.info('--------ALL TEST RESULTS----------')
    logging.info(f"RUNTIME: {runtime}")
    pprint(results_munch)


if __name__ == '__main__':
    sample_module_run()



