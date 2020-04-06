"""
allocate - jobs
"""
import json
import uuid
import asyncio_redis
from aiohttp import web
from redis import RedisError

from .redisclient import REDIS
from .settings import log


async def alljobs(request):
    """
    return all of the jobs in the queue
    """
    jobs = request.app["redis"].conn.hgetall("jobs")
    results = []
    for job in jobs.items():
        try:
            results.append(job[1].decode("utf-8"))
        except json.decoder.JSONDecodeError:
            log.error("failed to decode")
    results = [json.loads(result) for result in results]
    return web.json_response({"status": 200, "data": results})


async def onejob(request, allocation_id):
    """
    return single job
    """
    job = request.app["redis"].conn.hget("jobs", allocation_id)
    data = json.loads(job)
    return web.json_response({"status": 200, "data": data})


async def post(body):
    """
    saves a job in the queue
    """
    if "demands" in body:
        allocation_id = str(uuid.uuid4())
        log.debug("got post request")
        requirements = body["demands"]
        log.debug("demands: %s", requirements)
        payload = {
            "state": "free",
            "allocation_id": allocation_id,
            "demands": requirements,
        }
        try:
            REDIS.conn.hset("jobs", allocation_id, json.dumps(payload))
            return web.json_response(
                {"status": 200, "data": {"allocation_id": allocation_id}}
            )
        except RedisError as err:
            return web.json_response(
                {"status": 500, "reason": str(err)}, status=500
            )
    return web.json_response(
        {"status": 400, "reason": "'demands' missing from body"},
        status=400
    )


async def sub(request):
    """
    listens to redis jobs queue (subscribe)
    """
    log.debug("initiating jobs websocket")
    connection = await asyncio_redis.Connection.create(
        host=REDIS.host, port=REDIS.port
    )
    subscriber = await connection.start_subscribe()
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    request.app["websockets"].add(websocket)
    try:
        async for msg in websocket:
            payload = json.loads(msg.data)
            if "data" in payload:
                if "demands" in payload["data"]:
                    log.debug("processing demands")
                    resp = await post(payload["data"])
                    jresp = json.loads(resp.text)
                    if jresp["status"] == 200:
                        await websocket.send_json(
                            {"allocation_id": jresp["data"]["allocation_id"]}
                        )
                    continue
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
