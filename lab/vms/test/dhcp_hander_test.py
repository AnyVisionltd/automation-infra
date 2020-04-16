import pytest
from lab.vms import dhcp_handlers, libvirt_wrapper
import mock
import ipaddress


@pytest.fixture
def mock_libvirt():
    return mock.Mock(spec=libvirt_wrapper.LibvirtWrapper)


@pytest.mark.asyncio
async def test_libvirt_dhcp_allocate(event_loop, mock_libvirt):
    tested = dhcp_handlers.LibvirtDHCPAllocator(event_loop, mock_libvirt, "default")
    mock_libvirt.get_network_dhcp_info.return_value = {"net" : ipaddress.IPv4Network('192.168.20.1/24', strict=False),
                                                       "hosts" : ['192.168.20.2', '192.168.20.3']}
    ip = await tested.request_lease("1:2:3:4")
    mock_libvirt.get_network_dhcp_info.assert_called_once_with("default")
    mock_libvirt.add_dhcp_entry.assert_called_once_with('default', '192.168.20.3', '1:2:3:4')
    assert ip == '192.168.20.3'


@pytest.mark.asyncio
async def test_libvirt_dhcp_allocate_with_ip(event_loop, mock_libvirt):
    tested = dhcp_handlers.LibvirtDHCPAllocator(event_loop, mock_libvirt, "default")
    mock_libvirt.get_network_dhcp_info.return_value = {"net" : ipaddress.IPv4Network('192.168.20.1/24', strict=False),
                                                       "hosts" : ['192.168.20.2', '192.168.20.3']}
    ip = await tested.request_lease('1:2:3:4', '192.168.20.2')
    mock_libvirt.get_network_dhcp_info.assert_called_once_with("default")
    mock_libvirt.add_dhcp_entry.assert_called_once_with('default', '192.168.20.2', '1:2:3:4')
    assert ip == '192.168.20.2'


@pytest.mark.asyncio
async def test_libvirt_dhcp_allocate_no_ips(event_loop, mock_libvirt):
    tested = dhcp_handlers.LibvirtDHCPAllocator(event_loop, mock_libvirt, "default")
    mock_libvirt.get_network_dhcp_info.return_value = {"net" : ipaddress.IPv4Network('192.168.20.1/24', strict=False),
                                                       "hosts" : []}
    with pytest.raises(Exception):
        await tested.request_lease('1:2:3:4')
    mock_libvirt.get_network_dhcp_info.assert_called_once_with("default")


@pytest.mark.asyncio
async def test_libvirt_dhcp_allocate_incorrect_ip(event_loop, mock_libvirt):
    tested = dhcp_handlers.LibvirtDHCPAllocator(event_loop, mock_libvirt, "default")
    mock_libvirt.get_network_dhcp_info.return_value = {"net" : ipaddress.IPv4Network('192.168.20.1/24', strict=False),
                                                       "hosts" :  ['192.168.20.2', '192.168.20.3']}
    with pytest.raises(Exception):
        await tested.request_lease('1:2:3:4', '10.10.10.10')
    mock_libvirt.get_network_dhcp_info.assert_called_once_with("default")


@pytest.mark.asyncio
async def test_libvirt_dhcp_free(event_loop, mock_libvirt):
    tested = dhcp_handlers.LibvirtDHCPAllocator(event_loop, mock_libvirt, "default")
    await tested.release_lease('1:2:3:4')
    mock_libvirt.remove_dhcp_entry.assert_called_once_with('default', '1:2:3:4')
