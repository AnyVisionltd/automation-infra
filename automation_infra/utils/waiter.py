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


def await_changing_result(predicate, interval=2, tries=10):
    prev_res = predicate()
    for i in range(tries):
        time.sleep(interval)
        res = predicate()
        if res == prev_res:
            return res
        else:
            prev_res = res


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

