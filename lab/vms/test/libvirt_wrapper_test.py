from lab.vms import libvirt_wrapper
import mock
from mock import patch
import munch
import libvirt
import xmltodict

def _libvirt_mock():
    return mock.MagicMock(return_value=mock.MagicMock(spec=libvirt.virConnect))


@patch('libvirt.open', new_callable=_libvirt_mock)
def test_allocate_machine(libvirt_mock):
    tested = libvirt_wrapper.LibvirtWrapper("test_uri")
    machine_info = munch.Munch(name="sasha",
                               memsize=100,
                               num_cpus=10,
                               image="image.qcow",
                               net_ifaces=[{"macaddress":"1:1:1:1:1",
                                           "source" : "eth0",
                                           "mode" : "isolated"},
                                            {"macaddress":"2:2:2:2:2",
                                           "source" : "eth1",
                                           "mode" : "bridge"}],
                               sol_port=1000,
                               pcis=[{"domain" : '1',
                                      "bus" : '2',
                                      "slot" : '3',
                                      "function" : '4'},
                                    {"domain" : 'a',
                                      "bus" : 'b',
                                      "slot" : 'ff',
                                      "function" : 'dd'}])
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

