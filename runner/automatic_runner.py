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


def run_test_module(module_name):
    # TODO: this needs to run in new process
    pytest_args = [module_name, '-s', '-n 1', f'--html=report.html', '--self-contained-html']
    logging.info(f"pytest args: {pytest_args}")
    res = pytest.main(pytest_args)
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



