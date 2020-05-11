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
