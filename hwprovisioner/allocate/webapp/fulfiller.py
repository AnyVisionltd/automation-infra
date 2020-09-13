import asyncio
import concurrent
import time

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
        allocation_id = await self.redis.save_request(allocation_request)
        log.debug(f"trying to fulfill: {allocation_request}")

        potential_fulfillers = await self.find_potential_fulfillers(allocation_id)

        if not potential_fulfillers:
            await self.redis.update_status(allocation_id, status="unfulfillable",
                                     message="Allocator doesnt have resource_managers which can fulfill demands")
            return await self.redis.allocations(allocation_id)

        log.debug(f"found potential fulfillers: {potential_fulfillers}")
        async with self.fulfill_lock:
            while potential_fulfillers:
                chosen_rm = await self.choose_from(potential_fulfillers)
                log.debug(f"chosen rm: {chosen_rm}")
                potential_fulfillers.remove(chosen_rm)
                try:
                    result = await rm_requestor.allocate(chosen_rm['endpoint'], await self.redis.allocations(allocation_id))
                except concurrent.futures._base.CancelledError:
                    await self.release(allocation_id)
                except:
                    log.exception(f"{chosen_rm['alias']} couldnt fulfill demands. remaining potentials: "
                                  f"{[potential['alias'] for potential in potential_fulfillers]}")
                    continue
                log.debug(f'suceeded fullfilling request: {result}')
                await self._save_fulfilled_request(allocation_id, chosen_rm, result)
                return await self.redis.allocations(allocation_id)

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

    async def _save_fulfilled_request(self, allocation_id, resource_manager, allocation_result):
        hardware_details = list()
        for allocated_vm in allocation_result['info']:
            hardware_details.append(dict(
                ip=allocated_vm['net_ifaces'][0]['ip'],
                user='root',
                password='root',
                resource_manager_ep=resource_manager['endpoint'],
                vm_id=allocated_vm['name']
            ))
        await self.redis.update_status(allocation_id,
                                 resource_manager=resource_manager['endpoint'],
                                 hardware_details=hardware_details,
                                 result=allocation_result,
                                 status="success",
                                 expiration=int(time.time()) + 60,
                                 )

    async def release(self, allocation_id):
        log.debug(f"received release request for allocatin_id {allocation_id}")
        allocation = await self.redis.allocations(allocation_id)
        for hardware_details in allocation['hardware_details']:
            await rm_requestor.deallocate(hardware_details['vm_id'], hardware_details['resource_manager_ep'])
        await self.redis.update_status(allocation_id, status="deallocated")
        await self.redis.delete('allocations', [allocation_id])
