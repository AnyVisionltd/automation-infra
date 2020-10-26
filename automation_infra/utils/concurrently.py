import concurrent.futures
import logging


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



class Background(object):

    def __init__(self, jobs, *, max_workers=None):
        max_workers = max_workers or len(jobs)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        if isinstance(jobs, (list, tuple)):
            jobs = dict(enumerate(jobs))
        self._jobs = jobs

    def start(self):
        self._futures = prepare_jobs(self._executor, self._jobs)

    def wait(self, timeout=None):
        results = {}
        for future in concurrent.futures.as_completed(self._futures, timeout=timeout):
            job_id = self._futures[future]
            try:
                results[job_id] = future.result()
            except:
                logging.exception("When concurrently running '%(job_id)s'", dict(job_id=str(job_id)))
                raise
        return results

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
