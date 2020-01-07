"""
websocket logic for allocation
"""
import weakref
from aiohttp.web import WebSocketResponse

from .settings import log


async def ws_allocate(request):
    """
    Handles the allocation websocket connection from the requestor
    """
    websocket = WebSocketResponse()
    log.debug("initiating websocket")
    log.debug(dir(request.app))
    await websocket.prepare(request)
    request.app["websockets"] = weakref.WeakSet()
    request.app["websockets"].add(websocket)
    await websocket.send_json({"status": "connected"})

    try:
        async for msg in websocket:
            await websocket.send_json(
                {"status": "ok", "message": msg.json()}
            )
    finally:
        log.debug("websocket discarded")
        request.app["websockets"].discard(websocket)
    return websocket
