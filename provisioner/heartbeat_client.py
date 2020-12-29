import logging
import os
import threading
import time

import requests

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HeartbeatClient(object):
    def __init__(self, stop, ep, cert, key, interval=2):
        self.ep = ep
        self.stop_event = stop
        self.ssl_cert = cert
        self.ssl_key = key
        self.complete_cert = (cert, key)
        self.interval = interval

    def send_heartbeat(self, allocation_id):
        payload = {"allocation_id": allocation_id}
        response = requests.post("%s/api/heartbeat" % self.ep, json=payload, cert=self.complete_cert, verify=False)
        if response.status_code != 200:
            raise KeyError("Error sending heartbeat: %s", response.json())

    def send_heartbeats_until_stop(self, allocation_id):
        while True:
            if self.stop_event.is_set():
                break
            try:
                self.send_heartbeat(allocation_id)
            except KeyError:
                logging.error(f"send hb for {allocation_id} which doesnt exist on {self.ep}.. \nexiting pytest")
                os._exit(666)
            except:
                logging.warn(f"Failed to send ping to allocator {self.ep}", exc_info=True)
                time.sleep(0.1)
                continue
            time.sleep(self.interval)

    def send_heartbeats_on_thread(self, allocation_id):
        hb_thread = threading.Thread(target=self.send_heartbeats_until_stop, args=(allocation_id,), daemon=True)
        hb_thread.start()
        return hb_thread