"""
allocate - jobs
"""
import json
import uuid
from aiohttp import web
import asyncio_redis

from .redisclient import REDIS
from .settings import log


async def alljobs():
    """
    return all of the jobs in the queue
    """
    jobs = REDIS.conn.hgetall("jobs")
    results = []
    for job in jobs.items():
        try:
            results.append(job[1].decode("utf-8"))
        except json.decoder.JSONDecodeError:
            log.error("failed to decode")
    results = [json.loads(result) for result in results]
    return web.json_response({"status": 200, "data": results})


async def post(body):
    """
    saves a job in the queue
    """
    allocation_id = str(uuid.uuid4())
    log.debug("got post request")
    requirements = body["demands"]
    log.debug("demands: %s", requirements)
    payload = {
        "state": "free",
        "allocation_id": allocation_id,
        "demands": requirements,
    }
    REDIS.conn.hset("jobs", allocation_id, json.dumps(payload))
    return web.json_response(
        {"status": 200, "data": {"allocation_id": allocation_id}}
    )


async def sub(request):
    """
    listens to redis jobs queue (subscribe)
    """
    log.debug("initiating jobs websocket")
    connection = await asyncio_redis.Connection.create(
        host=REDIS.host, port=REDIS.port,
    )
    subscriber = await connection.start_subscribe()
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    request.app["websockets"].add(websocket)
    try:
        async for msg in websocket:
            payload = json.loads(msg.data)
            if payload["data"] == "all":
                log.debug("subscribing to all")
                await subscriber.subscribe(["jobs"])
            elif "allocation_id" in payload["data"]:
                log.debug(
                    "subscribing to jobqueue j:%s",
                    payload["data"]["allocation_id"],
                )
                await subscriber.subscribe(
                    ["j:%s" % payload["data"]["allocation_id"]]
                )
            while True:
                reply = await subscriber.next_published()
                await websocket.send_json(json.loads(reply.value))
    finally:
        await websocket.close()
        log.debug("websocket discarded")
        request.app["websockets"].discard(websocket)
    return websocket
