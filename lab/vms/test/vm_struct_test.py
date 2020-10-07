from lab.vms import vm
import pytest


@pytest.mark.asyncio
async def test_vm_json():
    net_ifaces = [{'macaddress': '52:54:00:8d:c0:07', 'mode': 'isolated', 'source': 'default'},
                  {'macaddress': '11:22:33:44:55:55', 'mode': 'bridge', 'source': 'eth0'}]
    expected_json = {'net_ifaces': net_ifaces,
                    'pcis': [],
                    'disks': [{'serial': 's1', 'device_name': 'dev1', 'image': 'image', 'type': 'hdd', 'size': 10}],
                    'name': 'name',
                    'num_cpus': 1,
                    'memsize': 1,
                    'sol_port': 2,
                    'base_image': 'image',
                    'api_version': 'v1',
                    'image' : 'image1',
                    'uuid' : "1234",
                    'cloud_init_iso' : None,
                    'base_image_size' : None,
                    'allocation_id': None,
                    'requestor': None}

    machine = vm.VM(name="name", num_cpus=1, memsize=1,
          net_ifaces=net_ifaces,
          sol_port=2,
          base_image='image',
          uuid = '1234',
          image='image1',
          disks=[{"serial": "s1",
                  "device_name": "dev1",
                  "image" : "image",
                  "type" : "hdd",
                  "size" : 10}])
    assert machine.json == expected_json

