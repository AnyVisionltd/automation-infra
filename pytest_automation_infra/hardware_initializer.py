"""
"""
import logging
import asyncio
import time

import aiohttp


machine_details = {
    "pass_machine": {
        "ip": "192.168.21.163",
        "user": "user",
        "password": "pass",
        "key_file_path": "",
        "host_id": 123,
        "host_type": "physical",
        "allocation_id": "",
    },
    "pem_machine": {
        "ip": "192.168.21.163",
        "user": "root",
        "password": "",
        "key_file_path": "/path/to/docker_user.pem",
        "host_id": 123,
        "host_type": "physical",
        "allocation_id": "",
    },
}


async def fetcher(hardware_req, provisioner, resource_wait=None):
    """
    send demands and listen for updates
    - resource_wait=None or number of seconds to wait until a resource is
      assigned
    """
    async with aiohttp.ClientSession() as client:
        logging.debug("connecting to job queue")
        websocket = await client.ws_connect(
            "%sapi/ws/jobs" % provisioner,
        )
        try:
            logging.debug("sending demands to job queue")
            await websocket.send_json({"data": {"demands": hardware_req}})
            reply = await websocket.receive_json(timeout=10)
            if "allocation_id" in reply:
                logging.debug(f"allocation_id: {reply['allocation_id']}")
                await websocket.send_json({
                    "data": {"allocation_id": reply["allocation_id"]}
                })
                reply = await websocket.receive_json(timeout=resource_wait)
                if "inventory_data" in reply:
                    return {
                        "candidate": reply["inventory_data"]["access"],
                        "allocation_id": reply["allocation_id"]
                    }
            else:
                logging.error("failed to set demands")
        except TimeoutError:
            logging.error("Error: timed out")
    return {}


def init_hardware(hardware_req, provisioner=None):
    """
    """
    hardware = {}
    if provisioner:  # provisioned mode
        logging.info(f"initing hardware with provisioner {provisioner}")
        loop = asyncio.get_event_loop()
        start = time.time()
        reply = loop.run_until_complete(fetcher(hardware_req, provisioner))
        logging.debug("fetcher took %s seconds", time.time() - start)
        if "candidate" in reply:
            logging.info(f'received hardware allocation: {reply}')
            hostname = list(hardware_req.keys())[0]
            hardware[hostname] = reply["candidate"]
            hardware[hostname]["alias"] = hostname
            hardware[hostname]["allocation_id"] = reply["allocation_id"]
        else:
            if "reason" not in reply:
                raise ValueError(
                    "failed to find a resource which met your requirements"
                )
            raise ValueError(reply["reason"])
    else:
        # hardware_req is a dictionary
        machine_names = hardware_req.keys()
        for machine_name in machine_names:
            hardware[machine_name] = machine_details[machine_name]
    return hardware
