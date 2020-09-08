import getpass
import json
import logging
import os
import socket
import time

import requests

import websocket

from pytest_automation_infra.settings import infra_logger


class ProvisionerClient(object):
    def __init__(self, ep=os.getenv('HABERTEST_PROVISIONER', "localhost:8080")):
        self.ep = ep

    def provision(self, hardware_req, timeout=120):
        hardware = {"machines": {}}
        ws = websocket.WebSocket()
        ws.connect("ws://%s/api/ws/jobs" % self.ep)
        start = time.time()
        while time.time() - start <= timeout:
            requestor_information = dict(hostname=os.getenv("host_hostname", socket.gethostname()),
                                         username=getpass.getuser(),
                                         ip=os.getenv("host_ip", socket.gethostbyname(socket.gethostname())))
            ws.send(json.dumps({"data": {"demands": hardware_req,
                                         "requestor": requestor_information}}))
            reply = json.loads(ws.recv())
            if reply['status'] == 'unfulfillable':
                infra_logger.info(f"response: {reply}")
                raise Exception(reply['message'])
            if reply['status'] == 'busy':
                infra_logger.debug(f"all resources currently busy.. trying again for {time.time() - start} seconds")
                time.sleep(5)
                continue
            if reply['status'] == 'success':
                hardware['allocation_id'] = reply['allocation_id']
                for machine_name, hardware_details in zip(hardware_req.keys(), reply['hardware_details']):
                    hardware['machines'][machine_name] = hardware_details
                infra_logger.debug("succeeded provisioning hardware")
                return hardware
        infra_logger.error(f"timed out trying to provision hardware {hardware_req}")
        raise TimeoutError(f"Timed out trying to provision hardware in {timeout} seconds")

    def release(self, allocation_id):
        resp = requests.delete(f'http://{self.ep}/api/release/{allocation_id}')
        res_json = resp.json()
        assert res_json['status'] == 200, f"Wasnt successful releasing {res_json}"

    def allocations(self):
        res = requests.get(f'http://{self.ep}/api/jobs')
        assert res.status_code == 200
        return res.json()['data']