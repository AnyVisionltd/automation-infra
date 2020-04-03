"""
resource manager - listener

the listener is responsible for listening to the allocation api for jobs,
determining if it is able to meet the demands of those jobs and if so,
volunteering (to the allocate api) to process them
"""
import asyncio
import aiohttp

from .config import CONFIG
from .settings import log


class Listener:
    """
    it is listeners responsibility to listen for jobs and to notify
    the job system (allocate service) that this resource manager is able
    to process those jobs
    """

    def __init__(self):
        """
        instantiate vars
        """
        self.job_inspection_cache = []  # naive memoization

    async def listen(self, app):
        """
        this method is intended to be ran for the duration of the resource
        managers life. it listens to the allocate api for jobs, then determines
        if this resource manager has the ability to satisfy those jobs. if so
        it volunteers for those jobs
        """
        while True:
            await asyncio.sleep(1)
            jobs = await self.get_jobs()
            if jobs:
                matches = await self.match_jobs_to_config(jobs)
                if matches:
                    await self.volunteer(app, matches)

    async def match_jobs_to_config(self, jobs):
        """
        iterates over parts of the config file and matches them to jobs
        """
        for rtype in ["static", "dynamic"]:
            if rtype in CONFIG["resources"]:
                return await self.matching_jobs(jobs, rtype)

    async def matching_jobs(self, jobs, rtype):
        """
        assess jobs to see if this resource manager has the ability to service
        their needs
        """
        log.debug("matching jobs ...")
        matches = []
        for job in jobs:
            if "allocation_id" in job and "state" in job:
                # naive: simple memoization
                if job["allocation_id"] in self.job_inspection_cache:
                    continue
                self.job_inspection_cache.append(job["allocation_id"])
                if job["state"] != "free":
                    continue

                for rref in CONFIG["resources"][rtype]:
                    match = await self.match(
                        job, rtype, rref, CONFIG["resources"][rtype][rref]
                    )
                    if match:
                        matches.append(match)
        return matches

    # currently only checks cpu, mem, labels and gpus
    async def match(self, job, rtype, rref, resource):
        """
        match a job to a resource
         - job. all job details (demands)
         - rtype. the reference type. static or dynamic
         - rref. the resource reference (a custom name, e.g. 'myserver')
         - resource. the resource information
        """
        jref = list(job["demands"])[0]
        job_demands = job["demands"][jref]
        log.debug("assessing %s for %s", job["allocation_id"], rref)
        fail = False
        for demand in job_demands:
            if demand not in resource:
                log.debug("%s has no %s field. skipping", rref, demand)
                fail = True
            if demand == "labels":
                fail = not await self.compare_labels(
                    job_demands["labels"], resource["labels"]
                )
            elif demand == "gpu":
                fail = not await self.compare_gpus(
                    job_demands["gpu"], resource["gpu"]
                )
            elif demand in ["cpu", "mem"]:
                fail = not await self.compare_cpuormem(
                    job_demands[demand], resource[demand]
                )
            else:
                log.warn(
                    "got a field that I wasn't sure how to handle: %s", demand
                )
                fail = True
            if fail:
                return None
        return {
            "allocation_id": job["allocation_id"],
            "inventory_ref": rref,
            "inventory_data": resource,
            "inventory_type": rtype,
            "job": job,
        }

    async def compare_labels(self, job_labels, resource_labels):
        """
        compares labels to be sure there's a match
        """
        matched = [k for k in job_labels if k in resource_labels]
        return len(matched) == len(job_labels)

    async def compare_gpus(self, job_gpus, resource_gpus):
        """
        compares gpus to be sure there's a match
        """
        for job_gpu in job_gpus:
            found = False
            for resource_gpu in resource_gpus:
                matched = {
                    k
                    for k in job_gpu
                    if k in resource_gpu and job_gpu[k] == resource_gpu[k]
                }
                if len(matched) == len(job_gpu):
                    found = True
                    break
            if not found:
                return False
        return True

    async def compare_cpuormem(self, job_demand, resource_demand):
        """
        compares cpu or memory to ensure demands are met
        """
        if ">=" in str(job_demand):
            if (resource_demand) >= int(job_demand.replace(">=", "")):
                return True
        else:
            if int(resource_demand) == int(job_demand):
                return True
        return False

    async def get_jobs(self):
        """
        grab all of the jobs currently in the queue
        """
        async with aiohttp.ClientSession() as client:
            async with client.get(
                "%sapi/jobs" % CONFIG["ALLOCATE_API"]
            ) as resp:
                data = await resp.json()
                return data["data"]
        return []

    @staticmethod
    async def volunteer(app, matches):
        """
        tell the allocate service that we are a candidate for processing some
        of its jobs
        """
        log.debug("volunteering ...")
        log.debug(
            "sending to %sapi/resourcemanager/%s"
            % (CONFIG["ALLOCATE_API"], CONFIG["UUID"])
        )
        async with aiohttp.ClientSession() as client:
            async with client.post(
                "%sapi/resourcemanager/%s"
                % (CONFIG["ALLOCATE_API"], CONFIG["UUID"]),
                json={"data": matches},
            ) as resp:
                data = await resp.json()
                if "status" not in data or data["status"] != 200:
                    log.error("failed to volunteer. %s", await resp.text)
