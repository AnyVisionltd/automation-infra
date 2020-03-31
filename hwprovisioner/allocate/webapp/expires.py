"""
allocate - expire (handles jobs expiring in redis)
"""
import asyncio
import json
import time

from .settings import log


async def expire(redis):
    """
    looks for expired jobs in redis and processes them
    """
    log.debug("processing expired jobs")
    jobs = redis.conn.hgetall("jobs")
    for job in jobs.values():
        data = json.loads(job)
        try:
            if data["expiration"] <= time.time():
                log.debug("found expired job! processing")
                log.debug(data)
                # publish expired event to dedicated inventory queue
                redis.conn.publish(
                    "i:%s-%s-%s"
                    % (
                        data["resourcemanager_id"],
                        data["inventory_type"],
                        data["inventory_ref"],
                    ),
                    json.dumps({"expired_job": data}),
                )
                log.debug("notified dedicated resource queue")
                redis.conn.hdel("jobs", data["allocation_id"])
                log.debug("deleted job")
        except KeyError as err:
            log.error("%s not found in jobs data", err)
        except Exception as err:
            log.error(err)
    await asyncio.sleep(10)
    await expire(redis)
