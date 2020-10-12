from concurrent.futures._base import CancelledError

import pytest
from lab.vms import allocator, vm
from lab.vms import vm_manager
from infra.utils import pci
from lab.vms import libvirt_wrapper
from lab.vms import image_store
from lab.vms import storage
from lab.vms import cloud_init
from lab.vms import dhcp_handlers
import mock
from aiohttp import web
from lab.vms import rest
import uuid


@pytest.fixture
def mock_libvirt():
    return mock.Mock(spec=libvirt_wrapper.LibvirtWrapper)


@pytest.fixture
def mock_image_store():
    return mock.Mock(spec=image_store.ImageStore)


@pytest.fixture
def mock_nbd_provisioner():
    return mock.Mock(spec=storage.NBDProvisioner)


@pytest.fixture
def mock_cloud_init():
    return mock.Mock(spec=cloud_init.CloudInit)


@pytest.fixture
def mock_dhcp_handler():
    return mock.Mock(spec=dhcp_handlers.DHCPManager)


def _generate_device(num_gpus):
    return [pci.Device(domain=dev, bus=dev, slot=dev,
                       function=dev, info={"current_link_speed": 1,
                                           "max_link_speed": 1,
                                           "max_link_width": 1,
                                           "current_link_width": "1",
                                           "local_cpulist": "1,2,3"}) for dev in range(num_gpus)]


def _generate_macs(num_macs):
    return ["00:00:00:00:00:%02x" % i for i in range(num_macs)]


async def test_vm_list(mock_libvirt, mock_image_store, aiohttp_client, loop, mock_nbd_provisioner, mock_cloud_init,
                       mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_libvirt.status.return_value = 'on'
    mock_cloud_init.generate_iso.return_value = "/tmp/iso_path"
    mock_dhcp_handler.allocate_ip = mock.AsyncMock(return_value="1.1.1.1")
    manager = vm_manager.VMManager(loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init,
                                   mock_dhcp_handler)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    with mock.patch("uuid.uuid4") as uuid4:
        uuid4.return_value = "uuid"
        with mock.patch("socket.socket"):
            await alloc.allocate_vm("sasha_image1", base_image_size=20, memory_gb=1, networks=["bridge"], num_cpus=2,
                                    num_gpus=1)

    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms

    app = web.Application()
    rest.HyperVisor(alloc, image_store, app)

    client = await aiohttp_client(app)
    resp = await client.get("/vms")
    vms = await resp.json()
    assert vms == {'vms': [{'name': 'sasha-vm-0', "uuid": "uuid", 'num_cpus': 2, 'memsize': 1, 'net_ifaces': [
        {'ip': '1.1.1.1', 'macaddress': '00:00:00:00:00:00', 'mode': 'bridge', 'source': 'eth0'}],
                            'pcis': ["0:0:0.0"], "api_version": "v1", "base_image": "sasha_image1",
                            'base_image_size': 20,
                            'image': '/home/sasha_king.qcow', 'disks': [], 'status': 'on', "sol_port": 1000,
                            'cloud_init_iso': '/tmp/iso_path',
                            'allocation_id': None, 'requestor': None}]}


async def test_vm_info(mock_libvirt, mock_image_store, aiohttp_client, loop, mock_nbd_provisioner, mock_cloud_init,
                       mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_libvirt.dhcp_lease_info.return_value = {'52:54:00:8d:c0:07': ['192.168.122.186', '192.168.122.187'],
                                                 '52:54:00:8d:c0:08': ['192.168.122.188']}
    mock_cloud_init.generate_iso.return_value = "/tmp/iso_path"
    mock_libvirt.status.return_value = 'on'
    mock_dhcp_handler.allocate_ip = mock.AsyncMock(return_value="1.1.1.1")

    manager = vm_manager.VMManager(loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init,
                                   mock_dhcp_handler)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)
    with mock.patch("socket.socket"):
        await alloc.allocate_vm("sasha_image1", memory_gb=1, base_image_size=20, networks=["bridge"], num_cpus=2,
                                num_gpus=1)
    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms

    app = web.Application()
    rest.HyperVisor(alloc, image_store, app)

    client = await aiohttp_client(app)
    resp = await client.get("/vms/sasha-vm-0")
    vm = await resp.json()
    assert vm == {'info': {'name': 'sasha-vm-0',
                           'disks': [], 'status': 'on',
                           'dhcp': {'52:54:00:8d:c0:07': ['192.168.122.186', '192.168.122.187'],
                                    '52:54:00:8d:c0:08': ['192.168.122.188']}}}


async def test_vm_allocate(mock_libvirt, mock_image_store, aiohttp_client, loop, mock_nbd_provisioner, mock_cloud_init,
                           mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_cloud_init.generate_iso.return_value = "/tmp/iso_path"
    mock_dhcp_handler.allocate_ip = mock.AsyncMock(return_value="1.1.1.1")

    manager = vm_manager.VMManager(loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init,
                                   mock_dhcp_handler)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)
    # Note that here we need to hack it in order not to bind to real port
    alloc._reserve_free_port = lambda x: x

    app = web.Application()
    rest.HyperVisor(alloc, image_store, app)

    client = await aiohttp_client(app)
    resp = await client.post("/vms", json={"base_image": "base.qcow",
                                           "ram": 100,
                                           "num_cpus": 1,
                                           "networks": ['bridge'],
                                           "num_gpus": 1,
                                           "disks": []})
    assert resp.status == 200
    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms


@pytest.fixture
def mock_allocator():
    return mock.AsyncMock(spec=allocator.Allocator)


async def test_vm_allocate_and_cancel(mock_allocator, mock_image_store, aiohttp_client, loop):
    app = web.Application()
    rest.HyperVisor(mock_allocator, mock_image_store, app)
    mock_allocator.allocate_vm.side_effect = [CancelledError, vm.VM("temp", 0, 10, 1000, "foo.bar"), CancelledError]
    client = await aiohttp_client(app)

    resp = await client.post("/vms", json={"base_image": "base.qcow",
                                    "name": "sasha",
                                    "ram": 100,
                                    "num_cpus": 1,
                                    "networks": ['bridge'],
                                    "num_gpus": 1,
                                    "disks": []})
    j = await resp.json()
    assert j == {'status': 'Cancelled'}

    resp = await client.post("/fulfill/now", json={"demands": {"host1": {}, "host2": {}},
                                                   "requestor": {"hostname": "unittest", "username": "user", "ip": "1.2.3.4", "creation_time": "2020-10-08 14:59:20.216747", "running_cmd": "lab/vms/test/test_rest.py unittest"},
                                                   "allocation_id": "f73a7520-a297-452a-8149-b3e84c66272f",
                                                   "status": "allocating", "expiration": 1602165740.4530108,
                                                   "rm_endpoint": "192.168.70.35:9080",
                                                   "message": "in progress"})
    j = await resp.json()
    assert j == {'status': 'Failed', 'error': 'error creating'}
    mock_allocator.destroy_vm.assert_called_with("temp")
