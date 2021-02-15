import logging
import time
import yaml
import paramiko

from automation_infra.plugins.admin import Admin

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
import os

from automation_infra.utils import waiter
import subprocess

logging.getLogger('paramiko').setLevel(logging.WARN)


def hardware_config(hardware, grouping=None):
    def wrapper(func):
        func.__hardware_reqs = hardware
        func.__cluster_config = grouping
        return func
    return wrapper


def is_k8s(connected_ssh_module):
    try:
        connected_ssh_module.execute("kubectl get po")
        return True
    except SSHCalledProcessError:
        return False


def get_catalog_credentials(url):
    home = os.getenv('HOME')
    helm_repo_config = f'{home}/.helm/repository/repositories.yaml'
    if not os.path.exists(helm_repo_config):
        raise FileNotFoundError(f"Couldnt find: {helm_repo_config}. run 'helm init --clien-only' to initiate helm config")
    with open(helm_repo_config, "r") as file:
        yaml_content = yaml.safe_load(file)
        for repo in yaml_content["repositories"]:
            if repo["url"] == url:
                creds_dict = {"username": repo["username"], "password": repo["password"]}
                return creds_dict
        raise AttributeError("Couldn't find catalog url in helm config, run 'helm repo add' to add catalog to helm config")


def do_docker_login(connected_ssh_module):
    logging.debug("doing docker login")
    host_running_test_ip = get_host_running_test_ip()
    remote_home = connected_ssh_module.execute("echo $HOME").strip()
    if host_running_test_ip != connected_ssh_module.get_ip():
        docker_login_host_path = f"{os.getenv('HOME')}/.docker/config.json"
        assert os.path.exists(docker_login_host_path) , "There is not docker credential in host running test"
        connected_ssh_module.execute(f"mkdir -p {remote_home}/.docker")
        connected_ssh_module.put(docker_login_host_path, f"{remote_home}/.docker/")
    connected_ssh_module.execute("docker login https://gcr.io")


def get_host_running_test_ip():
    return os.getenv("host_ip",
                     subprocess.check_output("hostname -I | awk '{print $1}'", shell=True).strip().decode('ascii'))


def local_timezone():
    with open("/etc/timezone", "r") as f:
        return f.read().strip()


def machine_id():
    return subprocess.check_output('sudo cat /sys/class/dmi/id/product_uuid', shell=True).decode().strip()


def sync_time(hosts):
    local_machine_id = machine_id()
    tz = local_timezone()
    for host in hosts.values():
        remote_machine_id = host.Admin.machine_id()
        if local_machine_id != remote_machine_id:
            host.Admin.set_timezone(tz)
