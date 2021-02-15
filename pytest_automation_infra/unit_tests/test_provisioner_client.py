"""
Can be run like: python -m pytest pytest_automation_infra/unit_tests/test_provisioner_client.py -s --log-cli-level=info
"""
import logging
import os
import threading
import time

import pytest

from pytest_provisioner import heartbeat_client, provisioner_client


def test_init_hardware_happy_flow():
    provisioner = provisioner_client.ProvisionerClient(
        ep=os.getenv('HABERTEST_PROVISIONER', "http://localhost:8080"),
        cert=os.getenv('HABERTEST_SSL_CERT', None),
        key=os.getenv('HABERTEST_SSL_KEY', None))
    stop = threading.Event()
    hb = heartbeat_client.HeartbeatClient(stop,
                                          ep=os.getenv('HABERTEST_HEARTBEAT_SERVER', "http://localhost:7080"),
                                          cert=os.getenv('HABERTEST_SSL_CERT', None),
                                          key=os.getenv('HABERTEST_SSL_KEY', None))
    req = {"host": {}}
    hardware = provisioner.provision(req)
    assert hardware
    allocation_id = hardware['allocation_id']
    logging.info(f"provisioned hardware successfully: {hardware}")
    logging.info("starting heartbeat")
    hb_thread = hb.send_heartbeats_on_thread(allocation_id)
    time.sleep(3)
    assert hb_thread.is_alive()
    logging.info("stopping heartbeat")
    stop.set()
    time.sleep(3)
    assert not hb_thread.is_alive()
    logging.info("starting heartbeat")
    stop.clear()
    hb_thread = hb.send_heartbeats_on_thread(allocation_id)
    time.sleep(3)
    assert hb_thread.is_alive()
    time.sleep(30)
    logging.info("stopping heartbeat")
    stop.set()
    logging.info("releasing hardware")
    provisioner.release(allocation_id)
    allocations = provisioner.allocations()
    assert allocation_id not in [allocation['allocation_id'] for allocation in allocations]
    with pytest.raises(KeyError):
        hb.send_heartbeat(allocation_id)
    logging.info("finished first part")

    # test expires
    logging.info("provisioning again")
    hardware = provisioner.provision(req)
    assert hardware
    allocation_id = hardware['allocation_id']
    logging.info("sending heartbeats")
    hb.send_heartbeat(allocation_id)
    hb_thread = hb.send_heartbeats_on_thread(allocation_id)
    time.sleep(5)
    logging.info("stopping heartbeats")
    stop.set()
    time.sleep(3)
    assert not hb_thread.is_alive()
    logging.info("waiting for expiration")
    time.sleep(35)
    allocations = provisioner.allocations()
    assert allocation_id not in [allocation['allocation_id'] for allocation in allocations]
    logging.info("passed test successfully!")

