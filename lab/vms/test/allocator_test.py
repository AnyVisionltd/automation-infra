import pytest
from lab.vms import allocator
from lab.vms import vm_manager
from infra.utils import pci
from lab.vms import libvirt_wrapper
from lab.vms import image_store
import asyncmock
from lab import NotEnoughResourceException
import mock


@pytest.fixture
def mock_libvirt():
    return mock.Mock(spec=libvirt_wrapper.LibvirtWrapper)


@pytest.fixture
def mock_image_store():
    return asyncmock.AsyncMock(spec=image_store.ImageStore)


def _generate_device(num_gpus):
    return [ pci.Device(domain=dev, bus=dev, slot=dev,
               function=dev, info={"current_link_speed" : 1,
                                "max_link_speed" : 1,
                                "max_link_width" : 1,
                                "current_link_width" : "1",
                                "local_cpulist" : "1,2,3"}) for dev in range(num_gpus)] 


def _generate_macs(num_macs):
    return ["00:00:00:00:00:%02x" % i for i in range(num_macs)]


def _verify_vm_valid(allocator, vm, expected_vm_name, expected_base_image, expected_gpus,
                     expected_networks, num_cpus, expected_mem, disks=None):
    disks = disks or []
    assert expected_vm_name in allocator.vms
    assert vm.image == expected_base_image
    assert vm.name == expected_vm_name
    networks = vm.net_ifaces
    assert len(networks) == len(expected_networks)
    for i, net in enumerate(networks):
        assert net['macaddress'] == expected_networks[i]['mac']
        assert net['mode'] == expected_networks[i]['type']
        assert net['source'] == expected_networks[i]['source']

    for i, gpu in enumerate(vm['pcis']):
        assert gpu.full_address == expected_gpus[i].full_address

    assert vm.num_cpus == num_cpus
    assert vm.memsize == expected_mem
    assert len(vm.disks) == len(disks)
    for i, disk in enumerate(vm.disks):
        assert disk['type'] == disks[i]['type']
        assert disk['image'] == disks[i]['image']
        assert disk['size'] == disks[i]['size']


@pytest.mark.asyncio
async def test_allocate_machine_happy_case(event_loop, mock_libvirt, mock_image_store):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(tested.vms) == 1
    vm = tested.vms['sasha-vm-0']
    _verify_vm_valid(tested, vm, expected_vm_name="sasha-vm-0",
                     expected_base_image="/home/sasha_king.qcow",
                     expected_gpus=gpu1,
                     expected_mem=1,
                     expected_networks=[{"mac" : macs[0], "type" : "bridge", "source" : "eth0"}],
                     num_cpus=2)

    mock_image_store.clone_qcow.assert_called_with("sasha_image1", "sasha-vm-0")
    mock_libvirt.define_vm.assert_called()

    # Now destroy the VM
    await tested.destroy_vm("sasha-vm-0")
    assert len(tested.vms) == 0
    assert tested.gpus_list == gpu1
    assert tested.mac_addresses == macs
    mock_image_store.delete_qcow.assert_called_with("/home/sasha_king.qcow")
    mock_libvirt.kill_by_name.assert_called_with("sasha-vm-0")


@pytest.mark.asyncio
async def test_allocate_machine_with_disks(event_loop, mock_libvirt, mock_image_store):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_image_store.create_qcow = asyncmock.AsyncMock(side_effect=["/home/disk1.qcow", "/home/disk2.qcow"])
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=1,
                             disks=[{"type": "ssd", "size" : 10},
                                    {"type" : "hdd", "size" : 5}])
    assert len(tested.vms) == 1
    vm = tested.vms['sasha-vm-0']
    _verify_vm_valid(tested, vm, expected_vm_name="sasha-vm-0",
                     expected_base_image="/home/sasha_king.qcow",
                     expected_gpus=gpu1,
                     expected_mem=1,
                     expected_networks=[{"mac" : macs[0], "type" : "bridge", "source" : "eth0"}],
                     num_cpus=2,
                     disks=[{"type" : "ssd", "size" : 10, "image": "/home/disk1.qcow"},
                            {"type" : "hdd", "size" : 5, "image": "/home/disk2.qcow"}])

    mock_image_store.clone_qcow.assert_called_with("sasha_image1", "sasha-vm-0")
    mock_libvirt.define_vm.assert_called()

    # Now destroy the VM
    await tested.destroy_vm("sasha-vm-0")
    assert len(tested.vms) == 0
    assert tested.gpus_list == gpu1
    assert tested.mac_addresses == macs
    # One for boot, one for ssd one for hdd
    assert mock_image_store.delete_qcow.call_count == 3
    deleted_images = set([call[0][0] for call in mock_image_store.delete_qcow.call_args_list])
    assert deleted_images == set(["/home/sasha_king.qcow", "/home/disk1.qcow","/home/disk2.qcow"])
    mock_libvirt.kill_by_name.assert_called_with("sasha-vm-0")

@pytest.mark.asyncio
async def test_kill_non_existing_vm(event_loop, mock_libvirt, mock_image_store):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(tested.vms) == 1

    with pytest.raises(Exception):
        await tested.destroy_vm("nonexisting")
    assert len(tested.vms) == 1

 
@pytest.mark.asyncio
async def test_allocate_machine_no_gpus(event_loop, mock_libvirt, mock_image_store):
    gpus = []
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)

    tested = allocator.Allocator(macs, gpus, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 1
    vm = tested.vms['sasha-vm-0']

    _verify_vm_valid(tested, vm, expected_vm_name="sasha-vm-0",
                     expected_base_image="/home/sasha_king.qcow",
                     expected_gpus=[],
                     expected_mem=1,
                     expected_networks=[{"mac" : macs[0], "type" : "bridge", "source" : "eth0"}],
                     num_cpus=2)

    mock_image_store.clone_qcow.assert_called_with("sasha_image1", "sasha-vm-0")
    # # FIXME: add assertion on call
    mock_libvirt.define_vm.assert_called()

    # Now destroy the VM
    await tested.destroy_vm("sasha-vm-0")
    assert len(tested.vms) == 0
    assert tested.gpus_list == []
    assert tested.mac_addresses == macs
    mock_image_store.delete_qcow.assert_called_with("/home/sasha_king.qcow")
    mock_libvirt.kill_by_name.assert_called_with("sasha-vm-0")


@pytest.mark.asyncio
async def test_allocate_more_vms_than_we_can(event_loop, mock_libvirt, mock_image_store):
    gpus = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    tested = allocator.Allocator(macs, gpus, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 1

    with pytest.raises(NotEnoughResourceException):
        await tested.allocate_vm("sasha_image2", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=0)

    assert len(tested.vms) == 1

    # Now destroy the VM
    await tested.destroy_vm("sasha-vm-0")
    assert len(tested.vms) == 0
    assert tested.gpus_list == gpus
    assert tested.mac_addresses == macs

    # Now we can allocate more
    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 1


@pytest.mark.asyncio
async def test_allocate_multiple(event_loop, mock_libvirt, mock_image_store):
    gpus = _generate_device(10)
    macs = _generate_macs(10)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(side_effect=["1.qcow", "2.qcow"])
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    tested = allocator.Allocator(macs, gpus, manager, "sasha", max_vms=3, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=2)
    assert len(tested.vms) == 1

    # Lets verify that we have 8 gpus and 9 nics left in pool
    assert len(tested.gpus_list) == 8
    assert len(tested.mac_addresses) == 9

    await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge", "isolated"], num_cpus=2, num_gpus=3)
    assert len(tested.vms) == 2

    # Lets verify that we have 8 gpus and 9 nics left in pool
    assert len(tested.gpus_list) == 5
    assert len(tested.mac_addresses) == 7

    # Now lets exaust gpus
    with pytest.raises(NotEnoughResourceException):
        await tested.allocate_vm("sasha_image1", memory_gb=1, networks=[], num_cpus=2, num_gpus=6)

    assert len(tested.vms) == 2
    assert len(tested.gpus_list) == 5
    assert len(tested.mac_addresses) == 7

    # Lets exaust macs
    with pytest.raises(NotEnoughResourceException):
        await tested.allocate_vm("sasha_image1", memory_gb=1, networks=["isolated"] * 8 , num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 2
    assert len(tested.gpus_list) == 5
    assert len(tested.mac_addresses) == 7


@pytest.mark.asyncio
async def test_start_stop_machine(event_loop, mock_libvirt, mock_image_store):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await alloc.allocate_vm("sasha_image1", memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms

    await manager.stop_vm(alloc.vms["sasha-vm-0"])
    mock_libvirt.poweroff_vm.assert_called_once()

    start_count = mock_libvirt.start_vm.call_count
    await manager.start_vm(alloc.vms["sasha-vm-0"])
    assert mock_libvirt.start_vm.call_count == start_count + 1


@pytest.mark.asyncio
async def test_machine_info(event_loop, mock_libvirt, mock_image_store):
    gpu1 = _generate_device(1)
    macs = _generate_macs(2)
    mock_image_store.clone_qcow = asyncmock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_libvirt.dhcp_lease_info.return_value = {'52:54:00:8d:c0:07': ['192.168.122.186'],
                                                 '52:54:00:8d:c0:08': ['192.168.122.187']}
    mock_libvirt.status.return_value = "on"

    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await alloc.allocate_vm("sasha_image1", memory_gb=1, networks=["isolated", "isolated"], num_cpus=2, num_gpus=1,
                            disks=[{"type": "ssd", "size" : 10},
                                    {"type" : "hdd", "size" : 5}])
    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms
    vm_info = await manager.info(alloc.vms['sasha-vm-0'])
    mock_libvirt.dhcp_lease_info.assert_called_once_with("sasha-vm-0")
    mock_libvirt.status.assert_called_once_with("sasha-vm-0")
    assert len(vm_info['disks']) == 2
    assert vm_info['status'] == 'on'
    assert vm_info['dhcp'] == {'52:54:00:8d:c0:07': ['192.168.122.186'],
                               '52:54:00:8d:c0:08': ['192.168.122.187']}
