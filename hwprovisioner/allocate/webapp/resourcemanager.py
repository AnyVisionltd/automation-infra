"""
allocate - resource manager
"""
import json

from aiohttp import web
import asyncio_redis

from .redisclient import REDIS
from .settings import log


async def heartbeat(request, body):
    """
    a resource manager has sent a heartbeat (this could be the first hb received ie rm just woke up
    or a continuation hb from a rm which is already working. It doesnt matter because the rm always sends
    all relevant data. So just insert the body to the relevant redis hkey
    """
    r_conn = await request.app["redis"].asyncconn
    rm_alias = body.get('alias')
    await r_conn.hset('resource_managers', rm_alias, json.dumps(body))
    return web.json_response({"status": 200})


async def volunteer(request, body, resourcemanager_id):
    """
    a resource manager has volunteered to process matched job(s) with it's
    resource(s) eventually. add this job onto the dedicated resource queue(s)
    so that it can attempt to process the job once it's free
    """
    log.debug("got volunteer(s)")
    if "data" in body:
        for volunteer in body["data"]:
            inv_id = f"{volunteer['inventory_type']}-{volunteer['inventory_ref']}"
            log.debug("publishing to i:%s-%s" % (resourcemanager_id, inv_id))
            request.app["redis"].conn.publish(
                "i:%s-%s"
                % (resourcemanager_id, inv_id), json.dumps(volunteer)
            )
        return web.json_response(
            {
                "status": 200,
            }
        )
    return web.json_response(
        {
            "status": "400",
            "reason": "'data' not in payload"
        },
        status=400
    )


async def volunteer_sub(request, resourcemanager_id, inventory_id):
    """
    this returns a websocket which when listened to will publish updates
    from a dedicated redis queue, designated for a resource managers inventory
    """
    log.debug("initiating inventory websocket")
    connection = await asyncio_redis.Connection.create(
        host=REDIS.host, port=REDIS.port
    )
    subscriber = await connection.start_subscribe()
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    request.app["websockets"].add(websocket)
    log.debug("subscribing to i:%s-%s", resourcemanager_id, inventory_id)
    await subscriber.subscribe(
        ["i:%s-%s" % (resourcemanager_id, inventory_id)]
    )
    try:
        while True:
            reply = await subscriber.next_published()
            await websocket.send_json(json.loads(reply.value))
    finally:
        await websocket.close()
        log.debug("websocket discarded")
        request.app["websockets"].discard(websocket)
    return websocket
