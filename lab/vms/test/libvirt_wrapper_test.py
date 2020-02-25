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

    # verify metadata
    metadata = vm_def['domain']['metadata']['vm:instance']

    assert metadata['net_ifaces'] == machine_info.net_ifaces
    assert metadata['pcis'] == ["1:2:3:4", "a:b:ff:dd"]
    assert metadata['name'] == machine_info.name
    assert metadata['num_cpus'] == str(machine_info.num_cpus)
    assert metadata['memsize'] == str(machine_info.memsize)
    assert metadata['sol_port'] == str(machine_info.sol_port)
    assert metadata['base_image'] == machine_info.base_image
    assert metadata['image'] == machine_info.image


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

@patch('libvirt.open', new_callable=_libvirt_mock)
def test_load_vm_domains(libvirt_mock):
    tested = libvirt_wrapper.LibvirtWrapper("test_uri")
    vm_lab_domain = mock.MagicMock(spec=libvirt.virDomain)
    vm_lab_domain.metadata.return_value = """
     <instance>
   <name>name</name>
   <num_cpus>1</num_cpus>
   <memsize>1</memsize>
   <net_ifaces>
      <macaddress>52:54:00:8d:c0:07</macaddress>
      <mode>isolated</mode>
      <source>default</source>
   </net_ifaces>
   <net_ifaces>
      <macaddress>11:22:33:44:55:55</macaddress>
      <mode>bridge</mode>
      <source>eth0</source>
   </net_ifaces>
   <sol_port>2</sol_port>
   <base_image>image</base_image>
   <disks>
      <serial>s1</serial>
      <device_name>dev1</device_name>
      <image>image</image>
      <type>hdd</type>
      <size>10</size>
   </disks>
   <_api_version>v1</_api_version>
</instance>
    """
    vm_non_lab_domain = mock.MagicMock(spec=libvirt.virDomain)
    vm_non_lab_domain.metadata.side_effect = libvirt.libvirtError("exception")
    libvirt_mock.return_value.listAllDomains.return_value = [vm_lab_domain, vm_non_lab_domain]
    vms_data = tested.load_lab_vms()
    assert len(vms_data) == 1
    assert vms_data[0] == munch.Munch({'name': 'name', 'num_cpus': '1', 'memsize': '1',
                           'net_ifaces': [{'macaddress': '52:54:00:8d:c0:07', 'mode': 'isolated', 'source': 'default'},
                                          {'macaddress': '11:22:33:44:55:55', 'mode': 'bridge', 'source': 'eth0'}],
                           'sol_port': '2',
                           'base_image': 'image',
                           'disks': [{'serial': 's1', 'device_name': 'dev1', 'image': 'image', 'type': 'hdd', 'size': '10'}],
                           '_api_version': 'v1'})

