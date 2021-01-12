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

from infra.utils import ip


class ProvisionerClient(object):
    def __init__(self, ep, cert=None, key=None):
        assert ep.startswith("http"), f"Provisioner endpoint needs to start with http. Received: {ep}"
        self.ep = ep
        self.external_ip = ip.external_ip()
        self.ssl_cert = (cert, key)
        self.ssl_context = None
        if cert:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(certfile=self.ssl_cert[0], keyfile=self.ssl_cert[1])

    def provision(self, hardware_req, timeout=120):
        hardware = {"machines": {}}
        for host_name, req in hardware_req.items():
            req.setdefault('base_image', 'automation_infra_1.0')
        use_ssl = True if self.ep.startswith("https") else False
        assert os.path.exists(self.ssl_cert[0]), f"Certfile doesnt exist at path: {self.ssl_cert[0]}"
        assert os.path.exists(self.ssl_cert[1]), f"Keyfile doesnt exist at path: {self.ssl_cert[1]}"
        try:
            ws = websocket.WebSocket(sslopt={"certfile": self.ssl_cert[0], "keyfile": self.ssl_cert[1], "cert_reqs": ssl.CERT_NONE} if use_ssl else None)
            ep = f'{"wss://" if use_ssl else "ws://"}{self.ep[self.ep.find("//")+2:]}/api/ws/jobs'
            ws.connect(ep)
        except:
            logging.exception("wasnt able to open websocket to provisioner. Stacktrace: ")
            raise
        start = time.time()
        allocation_id = str(uuid.uuid4())
        logging.info(f"allocation_id: {allocation_id}")
        while time.time() - start <= timeout:
            requestor_information = dict(hostname=os.getenv("host_hostname", socket.gethostname()),
                                         username=getpass.getuser(),
                                         ip=os.getenv("host_ip", socket.gethostbyname(socket.gethostname())),
                                         external_ip=self.external_ip,
                                         creation_time=str(datetime.now()),
                                         running_cmd=" ".join(sys.argv)
                                         )
            ws.send(json.dumps({"data": {"demands": hardware_req,
                                         "requestor": requestor_information,
                                         "allocation_id": allocation_id}}))
            reply = json.loads(ws.recv())
            if reply['status'] == 'unfulfillable':
                logging.info("\n\n test demands unfulfillable with current resource managers.. Exiting \n\n")
                os._exit(666)
            if reply['status'] == 'success':
                hardware['allocation_id'] = reply['allocation_id']
                for machine_name, hardware_details in zip(hardware_req.keys(), reply['hardware_details']):
                    hardware['machines'][machine_name] = hardware_details
                logging.debug("succeeded provisioning hardware")
                ws.close()
                return hardware
            else:
                logging.debug(f"received response: {reply['status']}")
                time.sleep(5)
                continue
        self.release(allocation_id)
        logging.error(f"timed out trying to provision hardware {hardware_req}. Exiting.")
        os._exit(666)

    def release(self, allocation_id):
        resp = requests.delete(f'{self.ep}/api/release/{allocation_id}', cert=self.ssl_cert, verify=False)
        res_json = resp.json()
        assert res_json['status'] == 200, f"Wasnt successful releasing {res_json}"

    def allocations(self):
        res = requests.get(f'{self.ep}/api/jobs', cert=self.ssl_cert, verify=False)
        assert res.status_code == 200
        return res.json()['data']