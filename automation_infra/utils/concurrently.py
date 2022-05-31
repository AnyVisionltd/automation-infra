import concurrent.futures
import logging
import time
from enum import Enum

from automation_infra.utils import waiter


def prepare_jobs(executor, jobs):
    job_futures = {}
    for job_id, job in jobs.items():
        if not isinstance(job, (list, tuple)):
            job = (job,)
        job_futures[executor.submit(job[0], *job[1:])] = job_id
    return job_futures


def run(jobs, *, max_workers=None, job_timeout=None):
    results = {}
    max_workers = max_workers or len(jobs)
    if isinstance(jobs, (list, tuple)):
        jobs = dict(enumerate(jobs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        job_futures = prepare_jobs(executor, jobs)
        for future in concurrent.futures.as_completed(job_futures, timeout=job_timeout):
            job_id = job_futures[future]
            try:
                results[job_id] = future.result()
            except:
                logging.exception("When concurrently running '%(job_id)s'", dict(job_id=str(job_id)))
                raise
    return results


def call(*callables):
    jobs = dict(enumerate(*callables))
    run(jobs)


class Completion(Enum):
    WAIT_ALL = 1
    WAIT_FIRST_SUCCESS = 2

    def to_future(self):
        return {Completion.WAIT_ALL : concurrent.futures.ALL_COMPLETED,
                Completion.WAIT_FIRST_SUCCESS : concurrent.futures.FIRST_COMPLETED}[self]


class Background(object):

    def __init__(self, jobs, *, max_workers=None):
        max_workers = max_workers or len(jobs)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        if isinstance(jobs, (list, tuple)):
            jobs = dict(enumerate(jobs))
        self._jobs = jobs

    def start(self):
        self._futures = prepare_jobs(self._executor, self._jobs)

    def wait(self, timeout=None, return_when=Completion.WAIT_ALL):

        def _make_result(futures):
            results = {}
            for fut in futures:
                job_id = self._futures[fut]
                try:
                    results[job_id] = fut.result()
                except:
                    logging.exception("When concurrently running '%(job_id)s'", dict(job_id=str(job_id)))
                    raise
            return results

        wait_futures = self._futures
        while len(wait_futures) > 0:
            done, not_done = concurrent.futures.wait(wait_futures, timeout=timeout, return_when=return_when.to_future())

            if return_when == Completion.WAIT_FIRST_SUCCESS:
                completed = [completion for completion in done if not completion.exception()]
                if len(completed):
                    logging.debug("Attempt to cancel all not completed")
                    [f.cancel() for f in not_done]
                    return _make_result(completed)

                # If we dont have any more features to wait .. we fail .. lets throw the last failure
                wait_futures = not_done
                if len(wait_futures) == 0:
                    raise done[0].exception()
                continue
            else:
                return _make_result(done)

    def force_stop(self, end_time=None, predicate=None, end_task=None):
        """in case you want to kill all threads in a certain way"""
        if end_time:
            time.sleep(end_time)
        if predicate:
            waiter.wait_for_predicate_nothrow(lambda: predicate, end_time)
        for future in self._futures:
            future.cancel()
        if end_task:
            end_task()


    @property
    def exception(self, timeout=0):
        for future in self._futures:
            try:
                return future.exception(timeout=timeout)
            except:
                return None
        return None


def start(jobs, max_workers=None):
    job = Background(jobs, max_workers=max_workers)
    job.start()
    return job
