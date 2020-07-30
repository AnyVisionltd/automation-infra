import json
import os
import time
import logging
import aiohttp


async def send_heartbeats(rm_info, allocator_ep):
    logging.debug(f'starting to send heartbeats with info: {rm_info}')
    while True:
        try:
            rm_info['last_hb'] = int(time.time())
            async with aiohttp.ClientSession() as client:
                uri = "http://%s/api/resource_manager/heartbeat" % allocator_ep
                logging.debug(f"sending heartbeat {rm_info} to url: {uri}")
                async with client.put(
                        uri, data=json.dumps(rm_info)) as resp:
                    data = await resp.json()
                    logging.debug(f"hb response: {data}")
                    if data['status'] != 200:
                        logging.exception("sent hb failed, is allocator configure correctly?")
                    time.sleep(5)
        except:
            continue
