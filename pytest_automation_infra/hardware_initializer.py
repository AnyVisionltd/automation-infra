
machine_details = {
    "pass_machine":
        {
            "ip": "192.168.21.163",
            "user": "user",
            "password": "pass",
            "key_file_path": "",
            "host_id": 123,
            "host_type": "physical",
            "allocation_id": "" 
        },
    "pem_machine":
        {
            "ip": "192.168.21.163",
            "user": "root",
            "password": "",
            "key_file_path": "/path/to/docker_user.pem",
            "host_id": 123,
            "host_type": "physical",
            "allocation_id": "" 
        }
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
