import logging
import time


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