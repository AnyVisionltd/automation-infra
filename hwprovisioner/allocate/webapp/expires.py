"""
allocate - expire (handles jobs expiring in redis)
"""
import asyncio
import json
import time

import aiohttp

from . import fulfiller, rm_requestor
from .settings import log


async def try_deallocate(ep, name):
    try:
        await rm_requestor.deallocate(name, ep)
    except:
        log.exception(f"failed deallocating {name} on ep {ep}")
        raise


async def deallocate(allocation):
    for hardware in allocation['hardware_details']:
        rm_ep = hardware['resource_manager_ep']
        vm_name = hardware["vm_id"]
        await try_deallocate(rm_ep, vm_name)


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
            if allocation['status'] not in ['received', 'allocating', 'success']:
                log.debug(f"found dangling {allocation_id} with status {allocation['status']}")
                result = await rm_requestor.check_status(allocation['allocation_id'], allocation['rm_endpoint'])
                log.debug(f"updated status: {result}")
                if result['info']:
                    log.debug(f"dangling resources, cleaning")
                    rm_ep = allocation['rm_endpoint']
                    for vm in result['info']:
                        vm_name = vm['name']
                        log.debug(f"should deallcate: {vm_name} on ep: {rm_ep}")
                        await try_deallocate(rm_ep, vm_name)
                        await redis.delete("allocations", allocation_id)
                        log.debug("deallocated successfully!")

            if allocation["expiration"] <= time.time():
                log.debug(f"found expired {allocation_id} with status {allocation['status']}")
                if allocation['status'] in ['success', 'allocated']:
                    log.debug(f"deallocating")
                    allocation['status'] = 'deallocating'
                    deallocate_tasks[allocation_id] = asyncio.ensure_future(deallocate(allocation))
                    await conn.hset("allocations", allocation["allocation_id"], json.dumps(allocation))
                else:
                    log.warning(f"found IMPROPER expired {allocation['status']} allocation {allocation_id}, removing")
                    await redis.delete("allocations", allocation_id)
            else:
                log.debug(f"job {allocation['allocation_id']} ttl: {allocation['expiration'] - int(time.time())}")

        for a_id, task in deallocate_tasks.items():
            try:
                await task
                await redis.delete("allocations", a_id)
            except:
                log.debug("exception deallocating")
                await redis.update_status(a_id, status='error_deallocating')

        await asyncio.sleep(10)
