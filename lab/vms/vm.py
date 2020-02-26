import munch
import asyncio
import json
import copy
import xmltodict


class VM(object):
    # This will be required to store/load vm info with "upgrade"
    OBJECT_VERSION = "v1"

    def __init__(self, name, num_cpus, memsize, sol_port, base_image,
                net_ifaces=None, pcis=None, disks=None, api_version=None,
                image=None):
        self.net_ifaces = net_ifaces or []
        self.pcis = pcis or []
        self.disks = disks or []
        self.name = name
        self.num_cpus = num_cpus
        self.memsize = memsize
        self.sol_port = sol_port
        self.base_image = base_image
        self.lock = asyncio.Lock()
        self.api_version = api_version or VM.OBJECT_VERSION
        self.image = image

    @property
    def json(self):
        return {"net_ifaces" : self.net_ifaces,
                "pcis" : [pci.full_address for pci in  self.pcis],
                "disks" : self.disks,
                "name"  : self.name,
                "num_cpus" : self.num_cpus,
                "memsize" : self.memsize,
                "sol_port" : self.sol_port,
                "base_image" : self.base_image,
                "api_version" : self.api_version,
                "image" : self.image}

    def __repr__(self):
        data = self.json
        data['locked'] = self.lock.locked()
        return str(data)