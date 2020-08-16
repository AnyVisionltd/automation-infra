"""
"""
import logging
import asyncio
import os
import time

import aiohttp
import yaml

def get_local_config(local_config_path):
    if not os.path.isfile(local_config_path):
        raise Exception("""local hardware_config yaml not found""")
    with open(local_config_path, 'r') as f:
        local_config = yaml.full_load(f)
    logging.debug(f"local_config: {local_config}")
    return local_config


async def fetcher(hardware_req, provisioner, resource_wait=None):
    """
    send demands and listen for updates
    - resource_wait=None or number of seconds to wait until a resource is
      assigned
    """
    async with aiohttp.ClientSession() as client:
        logging.debug("connecting to job queue")
        websocket = await client.ws_connect(
            "http://%s/api/ws/jobs" % provisioner,
        )
        try:
            logging.debug("sending demands to job queue")
            await websocket.send_json({"data": {"demands": hardware_req}})
            reply = await websocket.receive_json(timeout=60)
            if reply['status'] == 'success':
                return reply
            else:
                logging.info(f"response: {reply}")
                raise Exception(reply['message'])
        except TimeoutError:
            logging.error("Error: timed out")
    return {}


def provision_hardware(hardware_req, provisioner):
    """
    """
    hardware = {"machines": {}}
    if provisioner:  # provisioned mode
        logging.info(f"initing hardware with provisioner {provisioner}")
        loop = asyncio.get_event_loop()
        start = time.time()
        reply = loop.run_until_complete(fetcher(hardware_req, provisioner))
        logging.info("fetcher took %s seconds", time.time() - start)
        hardware['allocation_id'] = reply['allocation_id']
        for machine_name, hardware_details in zip(hardware_req.keys(), reply['hardware_details']):
            hardware['machines'][machine_name] = hardware_details
    return hardware


async def releaser(allocation_id, provisioner):
    async with aiohttp.ClientSession() as session:
        async with session.delete(f'http://{provisioner}/api/release/{allocation_id}') as resp:
            res_json = await resp.json()
            assert res_json['status'] == 200, f"Wasnt successful releasing {res_json}"
            return res_json


def release_hardware(hardware, provisioner):
    logging.info("releasing hardware")
    allocation_id = hardware['allocation_id']
    loop = asyncio.get_event_loop()
    reply = loop.run_until_complete(releaser(allocation_id, provisioner))
    logging.info(f"released hardware. response: {reply}")
