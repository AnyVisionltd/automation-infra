from subprocess import CalledProcessError

import requests

from automation_infra.plugins.ssh_direct import SshDirect
from infra.model import plugins


class Power(object):
    def __init__(self, host):
        self._host = host
        self.id = self._host.vm_id

    def verify_available(self):
        uuid = self._host.SshDirect.execute('sudo cat /sys/devices/virtual/dmi/id/product_uuid')
        if uuid.startswith("ec2"):
            raise NotImplementedError(
                "HUT appears to be an aws instance which is currently unsupported by Power plugin")
        assert bool(self._host.SshDirect.execute('cat /proc/cpuinfo | grep -i hypervisor || [[ $? == 1 ]]', timeout=3).strip()), \
            "Tried to power off a machine which isnt a vm"
        try:
            self.rm_ep = self._host.resource_manager_ep
        except KeyError:
            raise Exception("Please configure host's resource manager (in hardware.yaml) before using power plugin")
        self.url = f'http://{self.rm_ep}/vms/{self.id}'

    def off(self):
        self.verify_available()
        url = f'{self.url}/status'
        res = requests.post(url, json={"power": "off"})
        assert res.status_code == 200

    def on(self):
        url = f'{self.url}/status'
        res = requests.post(url, json={"power": "on"})
        assert res.status_code == 200

    def status(self):
        url = f'{self.url}'
        res = requests.get(url)
        assert res.status_code == 200
        return res.json()['info']['status']


plugins.register('Power', Power)
