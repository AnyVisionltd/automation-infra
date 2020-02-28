import time


def wait_for_predicate_nothrow(predicate, timeout=10, interval=1.0):
    before = time.time()
    caught_exceptions = ""
    while True:
        try:
            result = predicate()
            if result is not None:
                return result
        except Exception as e:
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

