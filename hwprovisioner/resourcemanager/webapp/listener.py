"""
resource manager - listener

the listener is responsible for listening to the allocation api for jobs,
determining if it is able to meet the demands of those jobs and if so,
volunteering (to the allocate api) to process them
"""
import json

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
            await asyncio.sleep(5)  # naive: allow processor to listen first
            jobs = await self.get_jobs()
            if jobs:
                matches = await self.matching_jobs(jobs)
                if matches:
                    await self.volunteer(app, matches)

    # note: this method needs A LOT of cleanup attention ...
    # currently only checks cpu, mem, labels and gpus
    async def matching_jobs(self, jobs):
        """
        assess jobs to see if this resource manager has the ability to service
        their needs
        """
        log.debug("matching jobs ...")
        matches = []
        for job in jobs:
            if "allocation_id" in job:
                allocation_id = job["allocation_id"]
                # naive: simple memoization
                if allocation_id in self.job_inspection_cache:
                    continue
                self.job_inspection_cache.append(allocation_id)

                jref = list(job["demands"])[0]
                # @todo: review efficiency - horrible loop nesting
                for rtype in ["static", "dynamic"]:
                    if rtype in CONFIG["resources"]:
                        for rref in CONFIG["resources"][rtype]:
                            log.debug(
                                "assessing %s for %s", allocation_id, rref
                            )
                            resource = CONFIG["resources"][rtype][rref]
                            fail = False
                            for demand in job["demands"][jref]:
                                # @todo: break these out into separate methods
                                if demand not in resource:
                                    log.debug(
                                        "%s has no %s field. skipping",
                                        rref,
                                        demand,
                                    )
                                    fail = True
                                    break
                                if demand == "labels":
                                    for lbl in job["demands"][jref]["labels"]:
                                        if lbl not in resource["labels"]:
                                            fail = True
                                            break
                                elif demand == "gpu":
                                    for gdemand in job["demands"][jref]["gpu"]:
                                        for rgpu in resource["gpu"]:
                                            if (
                                                gdemand not in rgpu
                                                or rgpu[gdemand]
                                                != job["demands"][jref]["gpu"][
                                                    gdemand
                                                ]
                                            ):
                                                fail = True
                                                break

                                        if fail:
                                            break
                                    if fail:
                                        break
                                elif demand in ["cpu", "mem"]:
                                    # we only support one comparisson for now
                                    if ">=" in job["demands"][jref][demand]:
                                        if (resource[demand]) < int(
                                            job["demands"][jref][
                                                demand
                                            ].replace(">=", "")
                                        ):
                                            fail = True
                                            break
                                    else:
                                        if int(resource[demand]) != int(
                                            job["demands"][jref][demand]
                                        ):
                                            fail = True
                                            break
                            if not fail:
                                matches.append(
                                    {
                                        "allocation_id": allocation_id,
                                        "inventory_ref": rref,
                                        "inventory_data": resource,
                                        "inventory_type": rtype,
                                        "job": job,
                                    }
                                )
        return matches

    async def get_jobs(self):
        """
        grab all of the jobs currently in the queue and filter out any that
        aren't free
        """
        jobs = []
        async with aiohttp.ClientSession() as client:
            async with client.get(
                "%sapi/jobs" % CONFIG["ALLOCATE_API"],
            ) as resp:
                data = await resp.json()
                for job in data["data"]:
                    job = json.loads(job)
                    if job["allocation_id"] not in self.job_inspection_cache:
                        if job["state"] == "free":
                            jobs.append(job)
        return jobs

    @staticmethod
    async def volunteer(app, matches):
        """
        tell the allocate service that we are a candidate for processing some
        of its jobs
        """
        # @todo: this approach is really inefficient. we should send all of
        #        the matches in a single request
        log.debug("volunteering ...")
        for match in matches:
            payload = {"data": match}
            log.debug(
                "sending to %sapi/resourcemanager/%s/%s-%s"
                % (
                    CONFIG["ALLOCATE_API"],
                    CONFIG["UUID"],
                    match["inventory_type"],
                    match["inventory_ref"],
                )
            )
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    "%sapi/resourcemanager/%s/%s-%s"
                    % (
                        CONFIG["ALLOCATE_API"],
                        CONFIG["UUID"],
                        match["inventory_type"],
                        match["inventory_ref"],
                    ),
                    json=payload,
                ) as resp:
                    data = await resp.json()
                    if "status" not in data or data["status"] != 200:
                        log.error("failed to volunteer")
