import getpass
import os
import socket
import time

import aiohttp
import pytest

from webapp import rm_requestor

RESOURCE_MANAGER = os.getenv("HABERTEST_RESOURCE_MANAGER", "localhost:9080")
PROVISIONER = os.getenv("HABERTEST_PROVISIONER", "localhost:8080")
HEARTBEAT_SERVICE = os.getenv("HABERTEST_HEARTBEAT_SERVER", "localhost:7080")

# These tests can be run in parallel by make test-provisioner

@pytest.mark.asyncio
async def test_resource_manager_requestor_happy_flow():
    """Set ip:port of RESOURCE_MANAGER_EP"""
    rm = dict(endpoint=RESOURCE_MANAGER)
    data = {"demands": {"host": {}},
            'requestor': dict(hostname=socket.gethostname(), username=getpass.getuser(), ip=socket.gethostbyname(socket.gethostname()))}
    possible = await rm_requestor.theoretically_fulfill(rm, data)
    assert possible
    allocate_result = await rm_requestor.allocate(rm['endpoint'], data)
    assert allocate_result['status'] == 'Success'
    vm_name = allocate_result['info'][0]['name']
    deallocate_result = await rm_requestor.deallocate(vm_name, rm['endpoint'])
    assert deallocate_result['status'] == 'Success'


async def request_hardware(demands):
    async with aiohttp.ClientSession() as client:
        websocket = await client.ws_connect("http://%s/api/ws/jobs" % PROVISIONER)
        await websocket.send_json({"data": {"demands": demands}})
        reply = await websocket.receive_json(timeout=60)
        assert reply['status'] == 'success', f"wasnt sucessful allocating {reply['message']}"
    return reply


async def send_heartbeat(allocation_id):
    async with aiohttp.ClientSession() as session:
        async with session.post(f'http://{HEARTBEAT_SERVICE}/api/heartbeat', json={"allocation_id": allocation_id}) as resp:
            res_json = await resp.json()
            assert res_json['status'] == 200, f"Wasnt successful sending heartbeat: {res_json}"


async def release(allocation_id):
    async with aiohttp.ClientSession() as session:
        async with session.delete(f'http://{PROVISIONER}/api/release/{allocation_id}') as resp:
            res_json = await resp.json()
            assert res_json['status'] == 200, f"Wasnt successful releasing {res_json}"


async def get_details(allocation_id):
    async with aiohttp.ClientSession() as client:
        async with client.get("http://%s/api/jobs/%s" % (PROVISIONER, allocation_id)) as resp:
            res_json = await resp.json()
            assert res_json['status'] == 200
    return res_json


@pytest.mark.asyncio
async def test_provision_expire_automatically():
    hardware_req = {"host": {}}
    reply = await request_hardware(hardware_req)
    allocation_id = reply['allocation_id']

    await send_heartbeat(allocation_id)
    time.sleep(35)

    details = await get_details(allocation_id)
    assert details['data']['status'] in ['deallocated', 'deallocating'], \
                f"Allocated job {allocation_id} wasnt deallocated automatically"


@pytest.mark.asyncio
async def test_provision_complete_flow():
    """Set ip:port of PROVISIONER, HEARTBEAT"""
    hardware_req = {"host": {}}
    reply = await request_hardware(hardware_req)
    allocation_id = reply['allocation_id']

    details = await get_details(allocation_id)
    assert details['data']['status'] == 'success', f"problem with job allocation status in redis"

    for i in range(2):
        await send_heartbeat(allocation_id)

    details = await get_details(allocation_id)
    expiration = details['data']['expiration']

    await send_heartbeat(allocation_id)
    details = await get_details(allocation_id)
    renewed_expiration = details['data']['expiration']
    assert renewed_expiration > expiration

    await release(allocation_id)
