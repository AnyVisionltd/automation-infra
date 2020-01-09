import logging
import time
import pprint

from runner import helpers

helpers.init_logger()

hardware_types = {
    "ori_pass":
        """{"host": {
                "ip": "192.168.21.163",
                "user": "user",
                "password": "pass",
                "key_file_path": "",
                "alias": "monster",
                "host_id": 123,
                "host_type": "physical",
                "allocation_id": "" }
                }
             """,
    "ori_pem":
        """{"host": {
                "ip": "192.168.21.163",
                "user": "root",
                "password": "",
                "key_file_path": "runner/docker_build/docker_user.pem",
                "alias": "monster",
                "host_id": 123,
                "host_type": "physical",
                "allocation_id": "" }
                }
             """,
    "gcr":
        """{"host": {
                    "ip": "35.231.0.137",
                    "user": "anyvision-devops",
                    "password": "",
                    "key_file_path": "/home/ori/Downloads/anyvision-devops.pem",
                    "alias": "gcloud",
                    "host_id": 123,
                    "host_type": "cloud",
                    "allocation_id": "" }
                }
             """,
    "sasha_vm":
        """{"host": {
                    "ip": "192.168.21.177",
                    "user": "root",
                    "password": "user1!",
                    "key_file_path": "",
                    "alias": "sasha_vm",
                    "host_id": 124,
                    "host_type": "on_prem",
                    "allocation_id": "" }
                }
             """,
    "ori_vm":
        """{"host": {
                    "ip": "192.168.122.45",
                    "user": "user",
                    "password": "user1!",
                    "key_file_path": "",
                    "alias": "ori_vm",
                    "host_id": 124,
                    "host_type": "virtual",
                    "allocation_id": "" }
                }
             """
}


def init_hardware(hardware_req):
    # TODO: here I would turn to a server admin service and get ips, userPass/sshKeys of the cluster
    # In the future there will be a real server provisioner which manages and returns hardware details,
    # and then the call would be something like this:
    # hardware = servers_manager.set_up(hardware_req)
    # TODO: but in addition to the cluster details, dont I also need to request services, like memsql, pipeng..?
    # For now, this place holder:

    # hardware_req is a dictionary
    hardware = {}
    machine_names = hardware_req.keys()
    for machine_name in machine_names:
        hardware[machine_name] = machine_details[machine_name]

    return hardware

    logging.info(f"successfully initialized hardware:\n{pprint.pformat(hardware)}")
    # TODO: Here I really need to run dev-ops tests which check that all hardware is working, no?
    # because the server_admin_service just gave me blank servers.

    return hardware
