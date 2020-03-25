"""
heartbeats - jobs
"""
import asyncio
import json
import uuid
import time
from aiohttp import web
import asyncio_redis

from .redisclient import REDIS
from .settings import log

redis_connection = {}


async def connect_to_redis():
    log.debug("creating connection to redis")
    redis_connection['redis'] = await asyncio_redis.Connection.create(
        host=REDIS.host, port=REDIS.port,
    )
    log.debug(f"set redis CONN! {redis_connection['redis']}")


async def heartbeat(request, body):
    """
    accepts a heartbeat, extending the resource reservation for an
    allocation_id
    """
    if not redis_connection:
        log.debug("connecting to redis...")
        await connect_to_redis()
    allocation_id = body['allocation_id']
    log.error(f"received heartbeat from allocation_id {allocation_id}")

    await update_expires(allocation_id)

    return web.json_response({"status": 200})


async def update_expires(allocation_id):
    """
    update the expires value inside redis
    """
    await asyncio.sleep(1)
    value = redis_connection['redis'].hget('jobs', allocation_id)
    try:
        d_value = json.loads(value)
    except TypeError:
        pass
    d_value['expiration'] = time.time() + 30
    redis_connection['redis'].hset('jobs', allocation_id, json.dumps(d_value))
