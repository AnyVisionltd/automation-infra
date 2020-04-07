"""
resource manager - processor
"""
from importlib import import_module
import json

import aiohttp

from plugins.plugin import ResourceManagerPlugin
from plugins.static.static import StaticPlugin
from webapp.config import CONFIG
from webapp.settings import log


class Processor:
    """
    all of the functionality for processing the inventory backlog
    """

    def __init__(self):
        """
        instantiate class globals
        """
        self.plugins = {}

    async def process(self, rtype, rref):
        """
        entrypoint. a process should be ran for each resource defined in the
        resources.yml provided to this service on run
        """
        async with aiohttp.ClientSession() as session:
            log.debug(
                "processor listening to %sapi/ws/resourcemanager/%s/%s-%s",
                CONFIG["ALLOCATE_API"],
                CONFIG["UUID"],
                rtype,
                rref,
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
                        if "allocation_id" in msg.data:
                            await self.handle_process(
                                rtype, rref, json.loads(msg.data)
                            )
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break

    async def handle_process(self, rtype, rref, data):
        """
        the logic for handling a process via an (optional) plugin
        if no plugin is found it will fallback to using the methods
        defined in this class
        """
        if data["allocation_id"] not in self.plugins:
            if rtype == "static":
                self.plugins[data["allocation_id"]] = StaticPlugin(
                    rtype, rref, data
                )
            else:
                try:
                    dmod = import_module("plugins." + rref + "." + rref)
                    dcls = getattr(dmod, rref.capitalize() + "Plugin")
                    if issubclass(dcls, ResourceManagerPlugin):
                        self.plugins[data["allocation_id"]] = dcls(
                            rtype, rref, data
                        )
                    else:
                        log.error(
                            "plugin is not a subclass of ResourceManagerPlugin"
                        )
                        return False
                except ModuleNotFoundError as err:
                    log.error("plugin not found for %s!", rref)
                    log.error(err)
                    return False
        if "inventory_data" in data:
            if await self.still_free(rtype, rref, data):
                # resource is ready. tell allocate to tell
                # tester that the resource is ready
                resp = await self.plugins[data["allocation_id"]].readyup()
                if not await self.validate_readyup_response(resp):
                    log.error("got an invalid response from the plugin:")
                    log.error(resp)
                    return False
                if await self.claim(resp):
                    log.debug("succeeded")
            else:
                log.debug("job was already claimed. ignoring")
        elif "expired_job" in data:
            await self.plugins[data["allocation_id"]].teardown()

    @staticmethod
    async def validate_readyup_response(resp):
        """
        validates that the response from the plugin conforms to the appropriate
        standards
        """
        return True

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

    async def claim(self, data):
        """
        claims a job. this will perform the necessary steps to ensure that a
        job will only be processed by this resource manager
        """
        log.debug("claiming ...")
        async with aiohttp.ClientSession() as client:
            async with client.post(
                "%sapi/claim" % CONFIG["ALLOCATE_API"],
                json=json.dumps(data)
            ) as resp:
                data = await resp.json()
                if "status" not in data or data["status"] != 200:
                    log.error("failed to volunteer")
                elif data["data"] == "claimed":
                    log.debug("claim successful")
                    return True
        return False
