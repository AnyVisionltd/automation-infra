"""
heartbeats - jobs
"""
import json
import time
from aiohttp import web

from .settings import log


async def heartbeat(request, body):
    """
    accepts a heartbeat, extending the resource reservation for an
    allocation_id
    """
    if "allocation_id" in body:
        allocation_id = body["allocation_id"]
        log.debug("received heartbeat from allocation_id %s", allocation_id)
        await update_expires(request, allocation_id)
        return web.json_response({"status": 200})
    else:
        return web.json_response(
            {"status": 400, "reason": "'allocation_id' missing from body"},
            status=400,
        )


async def update_expires(request, allocation_id):
    """
    update the expires value inside redis
    """
    conn = await request.app["redis"].asyncconn
    value = await conn.hget("allocations", allocation_id)
    d_value = json.loads(value)
    d_value["expiration"] = time.time() + 20
    await conn.hset("allocations", allocation_id, json.dumps(d_value))
    log.debug("expiration extended")
