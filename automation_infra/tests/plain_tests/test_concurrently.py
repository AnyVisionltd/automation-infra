import logging
import time
from automation_infra.utils import concurrently
import pytest


def test_concurrently():

    def _raise():
        raise Exception("Failed")

    def _success(sleep_time):
        time.sleep(sleep_time)
        return f"success_{sleep_time}"

    jobs = {"sleep" : lambda : _success(5),
            "success" : lambda:_success(1),
            "failure" : lambda: _raise()}

    bg = concurrently.Background(jobs)
    bg.start()
    with pytest.raises(Exception):
        bg.wait(timeout=None, return_when=concurrently.Completion.WAIT_ALL)

    bg = concurrently.Background(jobs)
    bg.start()
    result = bg.wait(timeout=None, return_when=concurrently.Completion.WAIT_FIRST_SUCCESS)
    assert len(result) == 1
    assert result['success'] == 'success_1'

    jobs = {"sleep" : lambda : _success(5),
            "success" : lambda:_success(1)}

    bg = concurrently.Background(jobs)
    bg.start()
    result = bg.wait(timeout=None, return_when=concurrently.Completion.WAIT_ALL)
    assert result == {'success': 'success_1', 'sleep': 'success_5'}


def test_concurrently_all_failures():

    def _raise():
        raise Exception("Failed")

    def _sleep_raise(sleep_time):
        time.sleep(sleep_time)
        raise Exception("Failed")

    jobs = {"sleep" : lambda : _sleep_raise(5),
            "success" : lambda:_sleep_raise(1),
            "failure" : lambda: _raise()}

    bg = concurrently.Background(jobs)
    bg.start()
    with pytest.raises(Exception):
        bg.wait(timeout=None, return_when=concurrently.Completion.WAIT_ALL)

    logging.info("Failed first success on all failed")
    bg = concurrently.Background(jobs)
    bg.start()
    with pytest.raises(Exception):
        result = bg.wait(timeout=None, return_when=concurrently.Completion.WAIT_FIRST_SUCCESS)
