"""
allocate - claim
"""
import json

from aiohttp import web

from .settings import log


async def claim(request, body):
    """
    claims a job for a resource manager
    """
    log.debug("got claim request %s", body)
    data = json.loads(body)
    request.app["redis"].conn.publish(
        "j:%s" % data["allocation_id"],
        body,
    )
    return web.json_response(
        {"status": 200, "data": "claimed"}
    )
