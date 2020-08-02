"""
allocate - expire (handles jobs expiring in redis)
"""
import asyncio
import json
import time

import aiohttp

from . import fulfiller, rm_requestor
from .settings import log


async def deallocate(data):
    for hardware in data['hardware_details']:
        rm_ep = hardware['resource_manager_ep']
        vm_name = hardware["vm_id"]
        try:
            await rm_requestor.deallocate(vm_name, rm_ep)
        except:
            log.exception(f"failed deallocating {vm_name} on ep {rm_ep}")
            raise


async def expire_allocations(redis):
    """
    looks for expired jobs in redis and processes them
    """
    conn = await redis.asyncconn
    while True:
        log.debug("processing expired jobs")
        deallocate_tasks = dict()
        allocations = await redis.allocations()
        for allocation_id, allocation in allocations.items():
            if "expiration" in allocation and allocation['status'] == 'success':
                if allocation["expiration"] <= time.time():
                    log.debug(f"found expired allocation {allocation['allocation_id']}! deallocating")
                    allocation['status'] = 'deallocating'
                    deallocate_tasks[allocation_id] = asyncio.ensure_future(deallocate(allocation))
                    await conn.hset("allocations", allocation["allocation_id"], json.dumps(allocation))
                else:
                    log.debug(f"job {allocation['allocation_id']} ttl: {allocation['expiration'] - int(time.time())}")

        for a_id, task in deallocate_tasks.items():
            allocation = allocations[a_id]
            try:
                await task
                await redis.delete("allocations", a_id)
            except:
                log.debug("exception deallocating")
                allocation['status'] = 'error_deallocating'
                await conn.hset("allocations", a_id, json.dumps(allocation))

        await asyncio.sleep(10)
