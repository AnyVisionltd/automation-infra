import pytest
from lab.vms import allocator, cloud_init
from lab.vms import vm_manager, dhcp_handlers
from infra.utils import pci
from lab.vms import libvirt_wrapper
from lab.vms import image_store
from lab import NotEnoughResourceException
import mock
from lab.vms import vm
import copy
import munch
from lab.vms import storage
from unittest.mock import call


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
    return [ pci.Device(domain=dev, bus=dev, slot=dev,
               function=dev, info={"current_link_speed" : 1,
                                "max_link_speed" : 1,
                                "max_link_width" : 1,
                                "current_link_width" : "1",
                                "local_cpulist" : "1,2,3"}) for dev in range(num_gpus)] 


def _generate_macs(num_macs):
    return ["00:00:00:00:00:%02x" % i for i in range(num_macs)]


def _verify_vm_valid(allocator, vm, expected_vm_name, expected_base_image, expected_gpus,
                     expected_networks, num_cpus, expected_mem, disks=None, base_image_size=None):
    disks = disks or []
    assert expected_vm_name in allocator.vms
    assert vm.image == expected_base_image
    assert vm.name == expected_vm_name
    assert vm.base_image_size == base_image_size
    networks = vm.net_ifaces
    assert len(networks) == len(expected_networks)
    for i, net in enumerate(networks):
        assert net['macaddress'] == expected_networks[i]['mac']
        assert net['mode'] == expected_networks[i]['type']
        assert net['source'] == expected_networks[i]['source']

    for i, gpu in enumerate(vm.pcis):
        assert gpu.full_address == expected_gpus[i].full_address

    assert vm.num_cpus == num_cpus
    assert vm.memsize == expected_mem
    assert len(vm.disks) == len(disks)
    for i, disk in enumerate(vm.disks):
        assert disk['type'] == disks[i]['type']
        assert disk['image'] == disks[i]['image']
        assert disk['size'] == disks[i]['size']


@pytest.mark.asyncio
async def test_allocate_machine_happy_case(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    mock_dhcp_handler.allocate_ip = mock.AsyncMock(return_value = "1.1.1.1")
    mock_cloud_init.generate_iso.return_value = "my_iso.iso"
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=10, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(tested.vms) == 1
    vm = tested.vms['sasha-vm-0']
    _verify_vm_valid(tested, vm, expected_vm_name="sasha-vm-0",
                     expected_base_image="/home/sasha_king.qcow",
                     expected_gpus=gpu1,
                     expected_mem=1,
                     expected_networks=[{"mac" : macs[0], "type" : "bridge", "source" : "eth0", "ip" : "1.1.1.1"}],
                     num_cpus=2,
                     base_image_size=10)

    mock_cloud_init.generate_iso.assert_called_with(vm)
    mock_dhcp_handler.allocate_ip.assert_called()
    mock_image_store.clone_qcow.assert_called_with("sasha_image1", "sasha-vm-0", 10)
    mock_libvirt.define_vm.assert_called()

    # Now destroy the VM
    await tested.destroy_vm("sasha-vm-0")
    assert len(tested.vms) == 0
    assert tested.gpus_list == gpu1
    assert tested.mac_addresses == macs
    mock_image_store.delete_qcow.assert_called_with("/home/sasha_king.qcow")
    mock_libvirt.kill_by_name.assert_called_with("sasha-vm-0")
    mock_dhcp_handler.deallocate_ip.assert_called_once()

def _find_disks_by_type(vm, disk_type):
    return [disk for disk in vm.disks if disk['type'] == disk_type]

@pytest.mark.asyncio
async def test_allocate_machine_with_disks(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_image_store.create_qcow = mock.AsyncMock(side_effect=["/home/disk1.qcow", "/home/disk2.qcow"])
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", base_image_size=None, memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=1,
                             disks=[{"type": "ssd", "size" : 10, "fs": "xfs"},
                                    {"type" : "hdd", "size" : 5, "fs": "ext4"}])
    assert len(tested.vms) == 1
    vm = tested.vms['sasha-vm-0']
    ssd = _find_disks_by_type(vm, "ssd")[0]
    hdd = _find_disks_by_type(vm, "hdd")[0]

    _verify_vm_valid(tested, vm, expected_vm_name="sasha-vm-0",
                     expected_base_image="/home/sasha_king.qcow",
                     expected_gpus=gpu1,
                     expected_mem=1,
                     expected_networks=[{"mac" : macs[0], "type" : "bridge", "source" : "eth0"}],
                     num_cpus=2,
                     disks=[ssd, hdd])

    provision_calls = [call(ssd['image'], 'xfs', ssd['serial']),
                       call(hdd['image'], 'ext4', hdd['serial'])]
    mock_nbd_provisioner.provision_disk.assert_has_calls(provision_calls, any_order=True)
    mock_image_store.clone_qcow.assert_called_with("sasha_image1", "sasha-vm-0", None)
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
async def test_kill_non_existing_vm(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=10, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(tested.vms) == 1

    with pytest.raises(Exception):
        await tested.destroy_vm("nonexisting")
    assert len(tested.vms) == 1

 
@pytest.mark.asyncio
async def test_allocate_machine_no_gpus(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpus = []
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)

    tested = allocator.Allocator(macs, gpus, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", base_image_size=None, memory_gb=1, networks=["bridge"], num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 1
    vm = tested.vms['sasha-vm-0']

    _verify_vm_valid(tested, vm, expected_vm_name="sasha-vm-0",
                     expected_base_image="/home/sasha_king.qcow",
                     expected_gpus=[],
                     expected_mem=1,
                     expected_networks=[{"mac" : macs[0], "type" : "bridge", "source" : "eth0"}],
                     num_cpus=2)

    mock_image_store.clone_qcow.assert_called_with("sasha_image1", "sasha-vm-0", None)
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
async def test_allocate_more_vms_than_we_can(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpus = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    tested = allocator.Allocator(macs, gpus, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 1

    with pytest.raises(NotEnoughResourceException):
        await tested.allocate_vm("sasha_image2", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=0)

    assert len(tested.vms) == 1

    # Now destroy the VM
    await tested.destroy_vm("sasha-vm-0")
    assert len(tested.vms) == 0
    assert tested.gpus_list == gpus
    assert tested.mac_addresses == macs

    # Now we can allocate more
    await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 1


@pytest.mark.asyncio
async def test_allocate_multiple(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpus = _generate_device(10)
    macs = _generate_macs(10)
    mock_image_store.clone_qcow = mock.AsyncMock(side_effect=["1.qcow", "2.qcow"])
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    tested = allocator.Allocator(macs, gpus, manager, "sasha", max_vms=3, paravirt_device="eth0", sol_base_port=1000)

    await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=2)
    assert len(tested.vms) == 1

    # Lets verify that we have 8 gpus and 9 nics left in pool
    assert len(tested.gpus_list) == 8
    assert len(tested.mac_addresses) == 9

    await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge", "isolated"], num_cpus=2, num_gpus=3)
    assert len(tested.vms) == 2

    # Lets verify that we have 8 gpus and 9 nics left in pool
    assert len(tested.gpus_list) == 5
    assert len(tested.mac_addresses) == 7

    # Now lets exaust gpus
    with pytest.raises(NotEnoughResourceException):
        await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=[], num_cpus=2, num_gpus=6)

    assert len(tested.vms) == 2
    assert len(tested.gpus_list) == 5
    assert len(tested.mac_addresses) == 7

    # Lets exaust macs
    with pytest.raises(NotEnoughResourceException):
        await tested.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["isolated"] * 8 , num_cpus=2, num_gpus=0)
    assert len(tested.vms) == 2
    assert len(tested.gpus_list) == 5
    assert len(tested.mac_addresses) == 7


@pytest.mark.asyncio
async def test_start_stop_machine(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(1)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await alloc.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms

    await manager.stop_vm(alloc.vms["sasha-vm-0"])
    mock_libvirt.poweroff_vm.assert_called_once()

    start_count = mock_libvirt.start_vm.call_count
    await manager.start_vm(alloc.vms["sasha-vm-0"])
    assert mock_libvirt.start_vm.call_count == start_count + 1


@pytest.mark.asyncio
async def test_machine_info(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(2)
    mock_image_store.clone_qcow = mock.AsyncMock(return_value="/home/sasha_king.qcow")
    mock_libvirt.dhcp_lease_info.return_value = {'52:54:00:8d:c0:07': ['192.168.122.186'],
                                                 '52:54:00:8d:c0:08': ['192.168.122.187']}
    mock_libvirt.status.return_value = "on"

    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    await alloc.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["isolated", "isolated"], num_cpus=2, num_gpus=1,
                            disks=[{"type": "ssd", "size" : 10, "fs" : "ext4"},
                                    {"type" : "hdd", "size" : 5, "fs" : "ext4"}])
    assert len(alloc.vms) == 1
    assert 'sasha-vm-0' in alloc.vms
    vm_info = await manager.info(alloc.vms['sasha-vm-0'])
    mock_libvirt.dhcp_lease_info.assert_called_once_with("sasha-vm-0")
    mock_libvirt.status.assert_called_once_with("sasha-vm-0")
    assert len(vm_info['disks']) == 2
    assert vm_info['status'] == 'on'
    assert vm_info['dhcp'] == {'52:54:00:8d:c0:07': ['192.168.122.186'],
                               '52:54:00:8d:c0:08': ['192.168.122.187']}


@pytest.mark.asyncio
async def test_delete_machines_on_start(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(1)
    macs = _generate_macs(2)
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    alloc = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)

    existing_vms = [vm.VM(name="name1", num_cpus=1, memsize=1,
                         net_ifaces=[], sol_port=2,
                         base_image='image').json,
                    vm.VM(name="name2", num_cpus=11, memsize=11,
                         net_ifaces=[], sol_port=22,
                         base_image='image').json]
    mock_libvirt.load_lab_vms.return_value = existing_vms
    await alloc.delete_all_dangling_vms()

    # Now lets make sure libvirt was called to destory vms
    mock_libvirt.kill_by_name.assert_has_calls([mock.call("name1"), mock.call("name2")])


def _adjust_machine_xml_to_libvirt_result(libvirt_xml):
    # Dont know why but when we read from libvirt metadata we get it without namespace
    # So this is what we need to do in the test
    return libvirt_xml.replace('<vm:instance xmlns:vm="anyvision">', '<instance>').replace('</vm:instance>', '</instance>')

def _emulate_libvirt_xml_dump_and_load(machine):
    xml = libvirt_wrapper.LibvirtWrapper.machine_metadata_xml(machine)
    xml = _adjust_machine_xml_to_libvirt_result(xml)
    return libvirt_wrapper.LibvirtWrapper.machine_metadata_xml_to_metadata(xml)

@pytest.mark.asyncio
async def test_create_machine_and_restore_machine(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(2)
    macs = _generate_macs(2)
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    mock_image_store.clone_qcow.return_value = "/tmp/image.qcow"
    mock_dhcp_handler.allocate_ip = mock.AsyncMock(return_value = "1.1.1.1")
    old_allocator = allocator.Allocator(copy.copy(macs), copy.copy(gpu1), manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)
    await old_allocator.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(old_allocator.vms) == 1
    assert 'sasha-vm-0' in old_allocator.vms
    old_vm_info = await manager.info(old_allocator.vms['sasha-vm-0'])

    # Get json with which machine was created
    vm_def = mock_libvirt.define_vm.call_args.args[0].json
    # Now set load to return same json
    mock_libvirt.load_lab_vms.return_value = [munch.Munch(vm_def)]

    # Now recreate the allocator
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)
    await tested.restore_vms()
    assert len(tested.vms) == 1
    assert 'sasha-vm-0' in tested.vms
    restored_vm_info = await manager.info(old_allocator.vms['sasha-vm-0'])

    assert restored_vm_info == old_vm_info


@pytest.mark.asyncio
async def test_restore_machine_fail_to_restore_network(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    gpu1 = _generate_device(2)
    macs = _generate_macs(2)
    mock_dhcp_handler.allocate_ip = mock.AsyncMock(return_value = "1.1.1.1")
    manager = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    mock_image_store.clone_qcow.return_value = "/tmp/image.qcow"
    old_allocator = allocator.Allocator(copy.copy(macs), copy.copy(gpu1), manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)
    await old_allocator.allocate_vm("sasha_image1", memory_gb=1, base_image_size=None, networks=["bridge"], num_cpus=2, num_gpus=1)
    assert len(old_allocator.vms) == 1
    assert 'sasha-vm-0' in old_allocator.vms

    # Get json with which machine was created
    vm_def = mock_libvirt.define_vm.call_args.args[0].json
    # Now set load to return same json
    mock_libvirt.load_lab_vms.return_value = [munch.Munch(vm_def)]

    # Now recreate the allocator
    mock_dhcp_handler.reallocate_ip = mock.AsyncMock(side_effect = Exception("Failed to allocate ip"))
    tested = allocator.Allocator(macs, gpu1, manager, "sasha", max_vms=1, paravirt_device="eth0", sol_base_port=1000)
    await tested.restore_vms()
    assert len(tested.vms) == 0
    # We still must have all resources that allocator was initializes with
    assert tested.mac_addresses == macs
    assert tested.gpus_list == gpu1
