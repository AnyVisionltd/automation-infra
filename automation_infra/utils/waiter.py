import logging
import signal
import time
from contextlib import contextmanager



def wait_for_predicate_nothrow(predicate, timeout=10, interval=1.0, exception_cls=Exception):
    before = time.time()
    caught_exceptions = ""
    while True:
        try:
            result = predicate()
            if result:
                return result
        except exception_cls as e:
            caught_exceptions = caught_exceptions + str(e) + "\n"
        if time.time() - before > timeout:
            raise TimeoutError("Predicate timed out, during the time we caught theses exceptions: \n" + caught_exceptions)
        time.sleep(interval)


def wait_for_predicate(predicate, timeout=10, interval=1.0):
    before = time.time()
    while not predicate():
        if time.time() - before > timeout:
            raise TimeoutError("Predicate timed out")
        time.sleep(interval)

def wait_nothrow(operation, timeout=10, interval=1.0):
    before = time.time()
    caught_exceptions = ""
    while True:
        try:
            return operation()
        except Exception as e:
            caught_exceptions = caught_exceptions + str(e) + "\n"
        if time.time() - before > timeout:
            raise TimeoutError("Predicate timed out, during the time we caught theses exceptions: \n" + caught_exceptions)
        time.sleep(interval)


def wait_for_predicates(*callables, timeout=60):
    for callable in callables:
        wait_nothrow(callable, timeout=timeout)


def await_changing_error_throwing(predicate, interval=2, tries=10):
    for i in range(tries):
        try:
            prev_res = predicate()
        except Exception:
            return
        time.sleep(interval)
    logging.info("out of tries")


def await_changing_result(predicate, interval=2, tries=10):
    prev_res = predicate()
    for i in range(tries):
        time.sleep(interval)
        res = predicate()
        if res == prev_res:
            return res
        else:
            prev_res = res


def await_changing_result_exception_accepting(predicate, interval=2, tries=10):
    try:
        prev_res = predicate()
    except Exception:
        prev_res = None

    for i in range(tries):
        time.sleep(interval)
        try:
            res = predicate()
        except Exception:
            res = None
        if res != prev_res:
            logging.info(i)
            return res
    logging.info("out of tries")


def await_and_aggregate_changing_until_result_match(predicate,expected_len_stop, interval=2, tries=10,timeout=30):
    """
        This function supports now only iterables results
        todo : this function need to support not only iterables reulsts and also get lambda for filter result match
    """
    caught_exceptions = ""
    res = []
    before = time.time()
    for i in range(tries):
        logging.info(f"fetch results try number - {i}")
        if time.time() - before > timeout:
            raise TimeoutError("Predicate timed out, during the time we caught theses exceptions: \n" + caught_exceptions)

        try:
            current_res = predicate()
        except Exception as e:
            caught_exceptions = caught_exceptions + str(e) + "\n"
            time.sleep(interval)
            continue

        if not _is_iterable(current_res):
            raise Exception("Did not get iterable object as result")

        res.extend(current_res)
        if len(res) >= expected_len_stop:
            break
        time.sleep(interval)
    return res


def await_for_stable_result(predicate, max_delta, stable_time, timeout):
    """create a range of possible results and verify the results are stable in this range for x time"""
    successes = 0
    sum = 0
    with time_limit(timeout):
        prev_res = predicate()
        while successes < stable_time:
            time.sleep(1)
            res = predicate()
            if prev_res - max_delta <= res <= prev_res + max_delta:
                successes += 1
                sum += res
            else:
                successes = 0
    return sum/stable_time


@contextmanager
def time_limit(seconds):
    """
    Enables a time_limit on function call. Use snippet:
    try:
        with waiter.time_limit(3):
            long_call()
    except TimeoutError:
        print("timed out!")
    """
    def signal_handler(signum, frame):
        raise TimeoutError("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def _is_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True
