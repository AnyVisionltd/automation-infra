import pytest
from lab.vms import image_store
import asyncmock
import mock
import asyncio
import asynctest
import uuid


def _subprocess_mock():
    mock = asyncmock.AsyncMock()
    mock.wait.return_value = asyncmock.AsyncMock(spec=asyncio.subprocess.Process)
    return mock

def _subprocess_cmd():
    return " ".join(asyncio.create_subprocess_exec.call_args[0])

@asynctest.mock.patch("asyncio.create_subprocess_exec", new_callable=_subprocess_mock)
@pytest.mark.asyncio
async def test_create_qcow_hdd(event_loop):
    tested = image_store.ImageStore(event_loop, "/root/base", '/root/run', '/root/ssd', '/root/hdd')
    asyncio.create_subprocess_exec.return_value.wait.return_value = 0
    image_path = await tested.create_qcow("sasha", "hdd", 10, "ser1")
    assert image_path == '/root/hdd/sasha_hdd_ser1.qcow2'
    assert _subprocess_cmd() == 'qemu-img create -f qcow2 /root/hdd/sasha_hdd_ser1.qcow2 10G'

@asynctest.mock.patch("asyncio.create_subprocess_exec", new_callable=_subprocess_mock)
@pytest.mark.asyncio
async def test_create_qcow_ssd(event_loop):
    tested = image_store.ImageStore(event_loop, "/root/base", '/root/run', '/root/ssd', '/root/hdd')
    asyncio.create_subprocess_exec.return_value.wait.return_value = 0
    image_path = await tested.create_qcow("sasha", "ssd", 10, "ser1")
    assert image_path == '/root/ssd/sasha_ssd_ser1.qcow2'
    assert _subprocess_cmd() == 'qemu-img create -f qcow2 /root/ssd/sasha_ssd_ser1.qcow2 10G'

