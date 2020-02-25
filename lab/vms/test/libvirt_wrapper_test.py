from lab.vms import libvirt_wrapper
import mock
from mock import patch
import libvirt
import xmltodict
from lab.vms import vm
from infra.utils import pci
import munch


def _libvirt_mock():
    return mock.MagicMock(return_value=mock.MagicMock(spec=libvirt.virConnect))


@patch('libvirt.open', new_callable=_libvirt_mock)
def test_allocate_machine(libvirt_mock):
    tested = libvirt_wrapper.LibvirtWrapper("test_uri")
    gpu1 = mock.Mock(spec=pci.Device)
    gpu1.full_address = "1:2:3:4"
    gpu2 = mock.Mock(spec=pci.Device)
    gpu2.full_address = "a:b:ff:dd"
    machine_info = vm.VM(name="sasha",
                               memsize=100,
                               num_cpus=10,
                               image="image.qcow",
                               base_image="base",
                               net_ifaces=[{"macaddress":"1:1:1:1:1",
                                           "source" : "eth0",
                                           "mode" : "isolated"},
                                            {"macaddress":"2:2:2:2:2",
                                           "source" : "eth1",
                                           "mode" : "bridge"}],
                               sol_port=1000,
                               pcis=[gpu1, gpu2])

    tested.define_vm(machine_info)
    libvirt_mock.assert_called_once_with("test_uri")
    assert libvirt_mock.return_value.defineXML.call_count == 1
    xml = libvirt_mock.return_value.defineXML.call_args[0][0]
    vm_def = xmltodict.parse(xml)
    assert vm_def['domain']['name'] == 'sasha'
    assert vm_def['domain']['memory']['#text'] == '100'
    assert vm_def['domain']['vcpu']['#text'] == '10'
    assert vm_def['domain']['devices']['disk']['source']['@file'] == 'image.qcow'
    assert vm_def['domain']['devices']['interface'][0]['mac']['@address'] == '1:1:1:1:1'
    assert vm_def['domain']['devices']['interface'][0]['source']['@network'] == 'eth0'
    assert vm_def['domain']['devices']['interface'][1]['mac']['@address'] == '2:2:2:2:2'
    assert vm_def['domain']['devices']['interface'][1]['source']['@mode'] == 'bridge'
    assert len(vm_def['domain']['devices']['hostdev']) == 2


@patch('libvirt.open', new_callable=_libvirt_mock)
def test_destroy_machine(libvirt_mock):
    tested = libvirt_wrapper.LibvirtWrapper("test_uri")

    # Let the vm returned by lookup be alive
    vm = libvirt_mock.return_value.lookupByName.return_value
    vm.isActive.return_value = True

    tested.kill_by_name("sasha2")

    libvirt_mock.assert_called_once_with("test_uri")
    libvirt_mock.return_value.lookupByName.assert_called_once_with("sasha2")
    assert vm.destroy.call_count == 1
    assert vm.undefine.call_count == 1


@patch('libvirt.open', new_callable=_libvirt_mock)
def test_dhcp_leases(libvirt_mock):
    tested = libvirt_wrapper.LibvirtWrapper("test_uri")

    # Let the vm returned by lookup be alive
    vm = libvirt_mock.return_value.lookupByName.return_value
    vm.interfaceAddresses.return_value = {'vnet0':
                {'addrs': [{'addr': '192.168.122.186', 'prefix': 24, 'type': 0},
                           {'addr': '192.168.122.187', 'prefix': 24, 'type': 0}], 'hwaddr': '52:54:00:8d:c0:07'},
                                          'vnet1':
                {'addrs': [{'addr': '192.168.122.188', 'prefix': 24, 'type': 0}], 'hwaddr': '52:54:00:8d:c0:08'}}

    expected_info = {'52:54:00:8d:c0:07': ['192.168.122.186', '192.168.122.187'],
                     '52:54:00:8d:c0:08': ['192.168.122.188']}
    actual_info = tested.dhcp_lease_info("sasha2")
    assert actual_info == expected_info
    libvirt_mock.assert_called_once_with("test_uri")
    libvirt_mock.return_value.lookupByName.assert_called_once_with("sasha2")
    assert vm.interfaceAddresses.call_count == 1

