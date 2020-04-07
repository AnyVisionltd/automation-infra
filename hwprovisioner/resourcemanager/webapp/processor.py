"""
resource manager - processor
"""
import json

import aiohttp

from webapp.config import CONFIG
from webapp.settings import log


class Processor:
    """
    all of the functionality for processing the inventory backlog
    """

    async def process(self, rtype, rref):
        """
        entrypoint. a process should be ran for each resource defined in the
        resources.yml provided to this service on run
        """
        async with aiohttp.ClientSession() as session:
            log.debug(
                "processor listening to %sapi/ws/resourcemanager/%s/%s-%s",
                CONFIG["ALLOCATE_API"], CONFIG["UUID"], rtype, rref
            )
            async with session.ws_connect(
                "%sapi/ws/resourcemanager/%s/%s-%s"
                % (CONFIG["ALLOCATE_API"], CONFIG["UUID"], rtype, rref)
            ) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        if msg.data == "close cmd":
                            await ws.close()
                            break
                        if "inventory_data" in msg.data:
                            data = json.loads(msg.data)
                            if await self.still_free(rtype, rref, data):
                                # resource is ready. tell allocate to tell
                                # tester that the resource is ready
                                resp = await self.ready_up(rtype, rref, data)
                                if await self.claim(resp):
                                    log.debug("succeeded")
                            else:
                                log.debug("job was already claimed. ignoring")
                        elif "expired_job" in msg.data:
                            data = json.loads(msg.data)
                            await self.teardown(data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break

    async def teardown(self, data):
        """
        invoked once a job has expired
        """
        log.debug("tearing down resource")

    async def still_free(self, rtype, rref, data):
        """
        check to see if we can still process this request
        """
        log.debug("checking to see if we can still process this request")
        async with aiohttp.ClientSession() as client:
            async with client.get(
                "%sapi/jobs/%s"
                % (CONFIG["ALLOCATE_API"], data["allocation_id"])
            ) as resp:
                assert resp.status == 200
                resp = await resp.json()
                try:
                    if resp["data"]["state"] == "free":
                        return True
                except KeyError as err:
                    log.error("didnt get expected response from job")
                    log.error(err)
        return False

    async def ready_up(self, rtype, rref, data):
        """
        initialize the resource if required. this should support spinning up
        vms on hardware or cloud

        returns object that will be consumed by the end user. this means that
        the object can be enriched (e.g. if we spin up a new VM, we may not
        know it's IP until this stage, so this is the place where you can
        insert that data into the payload to be consumed by pytest / the user)
        """
        if rtype == "dynamic":
            log.debug("readying up dynamic resource")
        return data

    async def claim(self, data):
        """
        claims a job. this will perform the necessary steps to ensure that a
        job will only be processed by this resource manager
        """
        log.debug("claiming ...")
        async with aiohttp.ClientSession() as client:
            async with client.post(
                "%sapi/claim" % CONFIG["ALLOCATE_API"], json=json.dumps(data)
            ) as resp:
                data = await resp.json()
                if "status" not in data or data["status"] != 200:
                    log.error("failed to volunteer")
                elif data["data"] == "claimed":
                    log.debug("claim successful")
                    return True
        return False

    @staticmethod
    def cleanup():
        """
        triggered when the app is destroyed (aiohttp on_cleanup)
        """
        log.debug("processor: cleanup")
