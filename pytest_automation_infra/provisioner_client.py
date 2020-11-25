import getpass
import json
import logging
import os
import ssl
import sys
import socket
import time
from datetime import datetime
import uuid

import requests

import websocket


class ProvisionerClient(object):
    def __init__(self, ep=os.getenv('HABERTEST_PROVISIONER', "http://localhost:8080"),
                       cert=os.getenv('SSL_CERT', None), key=os.getenv('SSL_KEY', None)):
        self.ep = ep
        self.ssl_cert = (cert, key)
        self.ssl_context = None
        if cert:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(self.ssl_key, self.ssl_cert)

    def provision(self, hardware_req, timeout=120):
        hardware = {"machines": {}}

        ws = websocket.WebSocket()
        use_ssl = True if self.ep.startswith("https") else False
        ws.connect(f'{"wss://" if use_ssl else "ws://"}{self.ep[self.ep.find("//")+2:]}/api/ws/jobs',  ssl=self.ssl_context if use_ssl else None)
        start = time.time()
        allocation_id = str(uuid.uuid4())
        logging.info(f"allocation_id: {allocation_id}")
        while time.time() - start <= timeout:
            requestor_information = dict(hostname=os.getenv("host_hostname", socket.gethostname()),
                                         username=getpass.getuser(),
                                         ip=os.getenv("host_ip", socket.gethostbyname(socket.gethostname())),
                                         external_ip=requests.get("http://ifconfig.me").text,
                                         creation_time=str(datetime.now()),
                                         running_cmd=" ".join(sys.argv)
                                         )
            ws.send(json.dumps({"data": {"demands": hardware_req,
                                         "requestor": requestor_information,
                                         "allocation_id": allocation_id}}))
            reply = json.loads(ws.recv())
            if reply['status'] == 'unfulfillable':
                logging.info(f"response: {reply}")
                raise Exception(reply['message'])
            if reply['status'] == 'busy':
                logging.debug(f"all resources currently busy.. trying again for {time.time() - start} seconds")
                time.sleep(5)
                continue
            if reply['status'] == 'success':
                hardware['allocation_id'] = reply['allocation_id']
                for machine_name, hardware_details in zip(hardware_req.keys(), reply['hardware_details']):
                    hardware['machines'][machine_name] = hardware_details
                logging.debug("succeeded provisioning hardware")
                return hardware
        self.release(allocation_id)
        logging.error(f"timed out trying to provision hardware {hardware_req}")
        raise TimeoutError(f"Timed out trying to provision hardware in {timeout} seconds")

    def release(self, allocation_id):
        resp = requests.delete(f'{self.ep}/api/release/{allocation_id}', cert=self.ssl_cert, verify=False)
        res_json = resp.json()
        assert res_json['status'] == 200, f"Wasnt successful releasing {res_json}"

    def allocations(self):
        res = requests.get(f'{self.ep}/api/jobs', cert=self.ssl_cert, verify=False)
        assert res.status_code == 200
        return res.json()['data']