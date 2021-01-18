import logging
import time

import pytest


@pytest.mark.parametrize('param', ["first", "second", "third"])
def test_parametrize(param):
    logging.info(f"running test {param}")


@pytest.mark.repeat(3)
def test_repeat(request):
    logging.info("running test_repeat")


def test_one():
    logging.info("Running test_one...")
    logging.debug(" debug Running test_one...")

    time.sleep(3)
    assert True
    logging.info("finished test one")


def test_two():
    logging.info("Running test_two...")
    logging.debug("debug Running test_two...")
    assert True
    time.sleep(1)
    logging.info("finished test two")


def test_three():
    logging.info("test three")
    logging.debug("debug test three")
    assert True
    time.sleep(1)
    logging.info("finished test three")