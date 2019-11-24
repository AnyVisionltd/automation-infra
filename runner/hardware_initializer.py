import time

hardware_types = {
    "aio":
        {"ori":
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
         "guy":
             """{"host": {
                    "ip": "35.199.172.249",
                    "user": "anyvision-devops",
                    "password": "",
                    "key_file_path": "/home/ori/Downloads/anyvision-devops.pem",
                    "alias": "gcloud",
                    "host_id": 123,
                    "host_type": "cloud",
                    "allocation_id": "" }
                }
             """
         }
}


def init_hardware(hardware_req):
    print("initilizing hardware...")
    # TODO: here I would turn to a server admin service and get ips, userPass/sshKeys of the cluster
    # In the future there will be a real server provisioner which manages and returns hardware details,
    # and then the call would be something like this:
    # hardware = servers_manager.set_up(hardware_req)
    # TODO: but in addition to the cluster details, dont I also need to request services, like memsql, pipeng..?
    # For now, this place holder:
    time.sleep(1)
    hardware = hardware_types[hardware_req["type"]]['ori']
    print("successfully initialized hardware!")
    print()
    # TODO: Here I really need to run dev-ops tests which check that all hardware is working, no?
    # because the server_admin_service just gave me blank servers.

    return hardware
