import logging
import os
import threading
import time

import requests


class HeartbeatClient(object):
    def __init__(self, stop, ep=os.getenv('HABERTEST_HEARTBEAT_SERVER', "localhost:7080"), interval=2):
        self.ep = ep
        self.stop_event = stop
        self.interval = interval

    def send_heartbeat(self, allocation_id):
        payload = {"allocation_id": allocation_id}
        response = requests.post("http://%s/api/heartbeat" % self.ep, json=payload)
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
            time.sleep(self.interval)

    def send_heartbeats_on_thread(self, allocation_id):
        hb_thread = threading.Thread(target=self.send_heartbeats_until_stop, args=(allocation_id,), daemon=True)
        hb_thread.start()
        return hb_thread