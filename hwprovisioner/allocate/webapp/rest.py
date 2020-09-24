"""
allocate - jobs
"""
import json
from aiohttp import web

from .fulfiller import Fulfiller
from .settings import log


async def alljobs(request):
    """
    return all of the jobs in the queue
    """
    allocations_raw = request.app["redis"].conn.hgetall("allocations")
    allocations_decoded = []
    for job in allocations_raw.items():
        try:
            allocations_decoded.append(job[1].decode("utf-8"))
        except json.decoder.JSONDecodeError:
            log.error("failed to decode")
    allocation_objects = [json.loads(allocation) for allocation in allocations_decoded]
    return web.json_response({"status": 200, "data": allocation_objects})


async def onejob(request, allocation_id):
    """
    return single job
    """
    job = request.app["redis"].conn.hget("allocations", allocation_id)
    data = json.loads(job)
    return web.json_response({"status": 200, "data": data})


async def fulfill(request):
    """
    request = {"data": {"demands": {"host": {"foo": "bar", "piz": "diez"}}}}}
    """
    # TODO: will this be a problem when we have more than 1 allocator? Could there be a situation where pytest
    #  queries one allocator but receives a response from a different one?? I hope not.. Or if an "allocator proxy"
    #  is sitting in front, how would this websocket work? the proxy would just forward the data forward?
    log.debug("initiating jobs websocket")
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    request.app["websockets"].add(websocket)
    try:
        async for msg in websocket:
            log.debug(f"received message on jobs WS: {msg}")
            payload = json.loads(msg.data)
            if "data" in payload:
                log.debug(f'processing demands: {payload["data"]}')
                try:
                    resp = await Fulfiller().fulfill(payload["data"])
                except Exception as e:
                    log.exception("got error trying to fulfill")
                    await websocket.send_json({"status": "exception", "message": str(e)})
                    continue  # continue here or return?
                log.debug(f"got response from fulfiller: {resp}")
                await websocket.send_json(resp)
                continue  # Return here? or could we have something else to do?
            else:
                log.debug(f"received message over websocket with unexpected data: {payload['data']}")
    finally:
        await websocket.close()
        log.debug("jobs websocket discarded")
        request.app["websockets"].discard(websocket)
    return websocket


async def release(request, allocation_id):
    log.debug(f"releasing allocation_id: {allocation_id}")
    await Fulfiller().release(allocation_id)
    return web.json_response({"status": 200})