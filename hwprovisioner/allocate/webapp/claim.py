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
    # updating job metadata
    job = request.app["redis"].conn.hget("jobs", data["allocation_id"])
    job_data = json.loads(job)
    job_data["state"] = "claimed"
    job_data["resourcemanager_id"] = data["resourcemanager_id"]
    job_data["inventory_type"] = data["inventory_type"]
    job_data["inventory_ref"] = data["inventory_ref"]
    request.app["redis"].conn.hset("jobs", data["allocation_id"], json.dumps(job_data))
    # adding connection info to dedicated job queue
    request.app["redis"].conn.publish(
        "j:%s" % data["allocation_id"],
        body,
    )
    return web.json_response(
        {"status": 200, "data": "claimed"}
    )
