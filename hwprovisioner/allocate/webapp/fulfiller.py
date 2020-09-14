import asyncio
import concurrent
import time
import uuid
from asyncio import shield

from . import rm_requestor
from .settings import log
from .redisclient import REDIS


class Fulfiller(object):
    def __init__(self):
        self.fulfill_lock = asyncio.Lock()
        self.redis = REDIS

    async def fulfill(self, allocation_request):
        """
        allocation_request = {"demands": {"host": {"whatever": "value", "foo": "bar"}},
                                "maybe_more_fields_like_priority_or_sender": "user|jenkins"}
        """
        allocation_id = allocation_request.get("allocation_id", str(uuid.uuid4()))
        allocation = await self.redis.allocations(allocation_id)
        if allocation:
            return allocation
        await self.redis.save_request(allocation_request)
        log.debug(f"trying to fulfill: {allocation_request}")

        potential_fulfillers = await self.find_potential_fulfillers(allocation_id)

        if not potential_fulfillers:
            allocation = await self.redis.allocations(allocation_id)
            allocation.update(status="unfulfillable", message="Allocator doesnt have resource_managers which can fulfill demands")
            await self.redis.delete(allocation_id)
            return allocation

        log.debug(f"found potential fulfillers: {potential_fulfillers}")
        async with self.fulfill_lock:
            log.debug("holding fulfill_lock")
            while potential_fulfillers:
                chosen_rm = await self.choose_from(potential_fulfillers)
                log.debug(f"chosen rm: {chosen_rm}")
                potential_fulfillers.remove(chosen_rm)
                try:
                    await self.redis.update_status(allocation_id,
                                                   status="allocating",
                                                   rm_endpoint=chosen_rm['endpoint'],
                                                   message="in progress")
                    result = await shield(rm_requestor.allocate(chosen_rm['endpoint'], await self.redis.allocations(allocation_id)))
                except asyncio.CancelledError:
                    log.debug(f"allocate task was cancelled.")
                    await self.redis.update_status(allocation_id, status="cancelled",
                                                   message="client cancelled after allocation started but before allocation was finish")
                    continue
                except Exception as e:
                    log.debug(f"exception {type(e)} when trying to allocate on rm {chosen_rm}")
                    await self.redis.update_status(allocation_id, status="exception", message=str(e))
                    log.exception(f"{chosen_rm['alias']} couldnt fulfill demands. remaining potentials: "
                                  f"{[potential['alias'] for potential in potential_fulfillers]}")
                    continue
                log.debug(f'suceeded fullfilling request: {result}')
                await self.redis.save_fulfilled_request(allocation_id, chosen_rm, result)
                return await self.redis.allocations(allocation_id)
        log.debug("released fulfill_lock")
        await self.redis.update_status(allocation_id, status="busy",
                                 message="Currently unable to fulfill requirements but should be able to in the future")
        return await self.redis.allocations(allocation_id)

    async def choose_from(self, resource_managers):
        # TODO: placeholder to enable some type of logic
        return resource_managers[0]

    async def find_potential_fulfillers(self, allocation_id):
        allocation_request = await self.redis.allocations(allocation_id)
        resource_managers = await self.redis.resource_managers()
        tasks = list()
        for resource_manager in resource_managers.values():
            tasks.append(rm_requestor.theoretically_fulfill(resource_manager, allocation_request))
        potentials = await asyncio.gather(*tasks, return_exceptions=True)
        potentials = [possible_rm for possible_rm in potentials if possible_rm is not None]
        log.debug(f"final potentials: {potentials}")
        return potentials

    async def release(self, allocation_id):
        allocation = await self.redis.allocations(allocation_id)
        if not allocation:
            return
        log.debug(f"received release request for allocation {allocation}")
        for hardware_details in allocation.get('hardware_details'):
            await rm_requestor.deallocate(hardware_details['vm_id'], hardware_details['resource_manager_ep'])
        await self.redis.update_status(allocation_id, status="deallocated")
        await self.redis.delete('allocations', [allocation_id])
