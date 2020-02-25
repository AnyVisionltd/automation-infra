import pytest
from lab.vms import image_store, libvirt_wrapper, vm_manager
import asyncmock
import mock
from lab.vms import vm


@pytest.fixture
def mock_libvirt():
    return mock.Mock(spec=libvirt_wrapper.LibvirtWrapper)


@pytest.fixture
def mock_image_store():
    return asyncmock.AsyncMock(spec=image_store.ImageStore)


@pytest.mark.asyncio
async def test_network_info_not_failing(event_loop, mock_libvirt, mock_image_store):
    tested = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    mock_libvirt.dhcp_lease_info.side_effect = Exception("exception")
    mock_libvirt.status.return_value = "on"

    vm_images = [{"serial": "s1",
                  "device_name": "dev1",
                  "image" : "image",
                  "type" : "hdd",
                  "size" : 10}]
    machine = vm.VM(name="name", num_cpus=1, memsize=1,
                         net_ifaces=[], sol_port=2,
                         base_image='image',
                         disks=vm_images)
    info = await tested.info(machine)
    assert info['status'] == 'on'


@pytest.mark.asyncio
async def test_load_vm_info(event_loop, mock_libvirt, mock_image_store):
    tested = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    vm_images = [{"serial": "s1",
                  "device_name": "dev1",
                  "image" : "image",
                  "type" : "hdd",
                  "size" : 10}]
    machine = dict(name="name", num_cpus=1, memsize=1,
                         net_ifaces=[], sol_port=2,
                         base_image='image',
                         disks=vm_images)
    mock_libvirt.load_lab_vms.return_value = [machine, machine]
    vms = await tested.load_vms_data()
    assert len(vms) == 2
    assert vms[0] == machine
    assert vms[1] == machine

