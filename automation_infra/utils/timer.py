from contextlib import contextmanager
from functools import wraps
import time
import logging
import functools



def timeitdecorator(func=None, log_level=logging.INFO, min_time=1):
    if func is None:
        return functools.partial(timeitdecorator, log_level=log_level, min_time=min_time)

    @wraps(func)
    def _time_it(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.time() - start
            if not min_time or duration > min_time:
                logging.log(log_level, f"{func}: execution time: {duration}s")
    return _time_it


@contextmanager
def timeit(alias=''):
    start = time.time()
    yield
    duration = time.time() - start
    if duration > 1:
        logging.debug(f"{alias} -> duration: {duration}")