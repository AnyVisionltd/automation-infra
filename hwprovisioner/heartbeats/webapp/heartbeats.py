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
    allocation_id = body["allocation_id"]
    log.debug("received heartbeat from allocation_id %s", allocation_id)
    await update_expires(request, allocation_id)
    return web.json_response({"status": 200})


async def update_expires(request, allocation_id):
    """
    update the expires value inside redis
    """
    conn = await request.app["redis"].asyncconn
    value = await conn.hget("jobs", allocation_id)
    d_value = json.loads(value)
    d_value["expiration"] = time.time() + 30
    await conn.hset("jobs", allocation_id, json.dumps(d_value))
    log.debug("expiration extended")
