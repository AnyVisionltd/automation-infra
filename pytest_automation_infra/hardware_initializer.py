"""
"""
import logging
import requests
import time

import aiohttp
import asyncio


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


async def fetcher(hardware_req, provisioner):
    """
    """
    logging.info("posting job to %sapi/jobs ", provisioner)
    payload = hardware_req
    logging.info("sending %s", payload)
    resp = requests.post("%sapi/jobs" % provisioner, json={"demands": payload})
    logging.info("got : %s", resp.text)
    jresp = resp.json()
    if "data" in jresp:
        if "allocation_id" in jresp["data"]:
            logging.info(
                "this task has been assigned allocation_id: %s",
                jresp["data"]["allocation_id"],
            )
            # have allocation id. listen to allocation queue
            async with aiohttp.ClientSession() as client:
                logging.debug("listening to job queue")
                websocket = await client.ws_connect(
                    "%sapi/ws/jobs" % provisioner,
                    autoclose=True,
                )
                payload = {
                    "data": {"allocation_id": jresp["data"]["allocation_id"]}
                }
                await websocket.send_json(payload)
                while True:
                    reply = await websocket.receive_json()
                    # listen for progress
                    if "inventory_data" in reply:
                        logging.debug("received hardware device!")
                        reply["inventory_data"]["access"]['allocation_id'] = reply['allocation_id']
                        return {"candidate": reply["inventory_data"]["access"]}
                    time.sleep(0.3)
        else:
            # no allocation_id
            logging.info("no allocation id")
    else:
        logging.error("didnt get expected response")
    return []


def init_hardware(hardware_req, provisioner=None):
    """
    """
    hardware = {}
    if provisioner:  # provisioned mode
        logging.info(f"initing hardware with provisioner {provisioner}")
        loop = asyncio.get_event_loop()
        reply = loop.run_until_complete(fetcher(hardware_req, provisioner))
        if "candidate" in reply:
            logging.info(f'received hardware allocation: {reply}')
            hostname = list(hardware_req.keys())[0]
            hardware[hostname] = reply["candidate"]
            hardware[hostname]["alias"] = hostname
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
