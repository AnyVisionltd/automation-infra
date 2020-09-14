"""
Can be run like: python -m pytest pytest_automation_infra/unit_tests/test_provisioner_client.py -s --log-cli-level=info
"""
import logging
import time

import pytest

from pytest_automation_infra import provisioner_client, heartbeat_client


def test_init_hardware_happy_flow():
    provisioner = provisioner_client.ProvisionerClient()
    stop = False
    hb = heartbeat_client.HeartbeatClient(lambda: stop)
    req = {"host": {}}
    hardware = provisioner.provision(req)
    assert hardware
    allocation_id = hardware['allocation_id']
    logging.info(f"provisioned hardware successfully: {hardware}")
    hb_thread = hb.send_heartbeats_on_thread(allocation_id)
    time.sleep(30)
    logging.info("stopping heartbeat")
    stop = True
    time.sleep(3)
    assert not hb_thread.isAlive()
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
    stop = True
    time.sleep(3)
    assert not hb_thread.isAlive()
    logging.info("waiting for expiration")
    time.sleep(35)
    allocations = provisioner.allocations()
    assert allocation_id not in [allocation['allocation_id'] for allocation in allocations]
    logging.info("passed test successfully!")

