import json
import time

# cluster = {"host1": {"ram": 10, "host_type": "virtual"},
#            "host2" : {"gpu": (1,), "gpu_type": "1080Ti"}}
from infra.model.base_config import BaseConfig, DefaultFactoryMunch


def init_hardware(cluster):
    print("initilizing hardware...")
    # TODO: here I would turn to a server admin service and get ips, userPass/sshKeys of the cluster
    # base_config = servers_manager.set_up(cluster)
    # TODO: but in addition to the cluster details, dont I also need to request services, like memsql, pipeng..?
    # For now, this place holder:
    time.sleep(1)
    import os
    with open("runner/base_config.json", 'r') as f:
        j = json.load(f)
    base_config = BaseConfig.fromDict(j, DefaultFactoryMunch)
    print("successfully initialized hardware!")
    print()
    # TODO: Here I really need to run dev-ops tests which check that all hardware is working, no?
    # because the server_admin_service just gave me blank servers.

    return base_config

