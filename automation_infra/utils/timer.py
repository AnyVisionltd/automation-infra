from contextlib import contextmanager
from functools import wraps
import time
import logging


def timeitdecorator(func):
    @wraps(func)
    def _time_it(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.time() - start
            if duration > 1:
                logging.info(f"{func}: execution time: {duration}s")
    return _time_it


@contextmanager
def timeit(alias=''):
    start = time.time()
    yield
    duration = time.time() - start
    if duration > 1:
        logging.info(f"{alias} -> duration: {duration}")