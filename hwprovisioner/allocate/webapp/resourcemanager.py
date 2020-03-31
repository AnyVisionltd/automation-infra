"""
allocate - resource manager
"""
import json

from aiohttp import web
import asyncio_redis

from .redisclient import REDIS
from .settings import log


async def volunteer(request, body, resourcemanager_id, inventory_id):
    """
    a resource has volunteered to do this job eventually. add this job onto the
    resource managers inventory queue so that it can attempt to process the job
    once it's free
    """
    log.debug("got a volunteer")
    log.debug("publishing to i:%s-%s" % (resourcemanager_id, inventory_id))
    request.app["redis"].conn.publish(
        "i:%s-%s" % (resourcemanager_id, inventory_id), json.dumps(body["data"])
    )
    return web.json_response(
        {
            "status": 200,
            "data": {"queue": "i:%s-%s" % (inventory_id, resourcemanager_id)},
        }
    )


async def volunteer_sub(request, resourcemanager_id, inventory_id):
    """
    this returns a websocket which when listened to will publish updates
    from a dedicated redis queue, designated for a resource managers inventory
    """
    log.debug("initiating inventory websocket")
    connection = await asyncio_redis.Connection.create(
        host=REDIS.host, port=REDIS.port,
    )
    subscriber = await connection.start_subscribe()
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    request.app["websockets"].add(websocket)
    log.debug("subscribing to i:%s-%s" % (resourcemanager_id, inventory_id))
    await subscriber.subscribe(["i:%s-%s" % (resourcemanager_id, inventory_id)])
    try:
        while True:
            reply = await subscriber.next_published()
            await websocket.send_json(json.loads(reply.value))
    finally:
        await websocket.close()
        log.debug("websocket discarded")
        request.app["websockets"].discard(websocket)
    return websocket
