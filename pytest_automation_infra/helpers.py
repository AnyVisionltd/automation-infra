import logging
import subprocess,os
from os import path
from infra.plugins.ssh_direct import SSHCalledProcessError
from infra.plugins.ssh import SSH
from infra.plugins.ssh_direct import SshDirect
from infra.utils import shell

def hardware_config(hardware):
    def wrapper(func):
        func.__hardware_reqs = hardware
        return func
    return wrapper


def use_gravity_exec(connected_ssh_module):
    if is_k8s(connected_ssh_module):
        return 'sudo gravity exec'
    else:
        return ''


def is_k8s(connected_ssh_module):
    try:
        connected_ssh_module.execute("sudo kubectl get po")
        return True
    except SSHCalledProcessError:
        return False


def deploy_proxy_container(connected_ssh_module, auth_args=['password', 'root', 'pass']):
    removed = remove_proxy_container(connected_ssh_module)
    if removed:
        logging.warning("Unexpected behavior: removed proxy container despite that I shouldn't have needed to")

    logging.info("initializing docker")
    run_cmd = f'{use_gravity_exec(connected_ssh_module)} docker run -d --rm --network=host --name=ssh_container orihab/ubuntu_ssh:2.0 {" ".join(auth_args)}'
    connected_ssh_module.execute(run_cmd)
    logging.info("docker is running")


def init_docker_and_connect(host):
    logging.info(f"[{host}] connecting to ssh directly")
    host.SshDirect.connect()
    logging.info(f"[{host}] connected successfully")

    deploy_proxy_container(host.SshDirect)

    logging.info(f"[{host}] connecting to ssh container")
    host.SSH.connect()
    logging.info(f"[{host}] connected successfully")


def init_dockers_and_connect(hosts):
    for name, host in hosts:
        logging.info(f"[{name}: {host}] initializing machine ")
        init_docker_and_connect(host)
        logging.info(f"[{name}: {host}] success initializing docker and connecting to it")


def remove_proxy_container(connected_ssh_module):
    try:
        logging.info("trying to remove docker container")
        connected_ssh_module.execute(f'{use_gravity_exec(connected_ssh_module)} docker rm -f ssh_container')
        logging.info("removed successfully!")
        return True
    except SSHCalledProcessError as e:
        if 'No such container' not in e.stderr:
            raise e
        logging.info("nothing to remove")


def collect_logs(hosts,local_path, remote_path):
    hosts['host'].SshDirect.execute("if [! -d '/tmp/logs' ]; then mkdir /tmp/logs/; fi")
    hosts['host'].SshDirect.execute(f"tar cf - {remote_path} | pigz > /tmp/logs/run_logs.tar.gz")
    hosts['host'].SshDirect.download(f"{local_path}", "/tmp/logs/run_logs.tar.gz")
    os.system(f"sudo chmod 777 {local_path}/run_logs.tar.gz ")
    os.chdir(f"{local_path}/")
    os.system(f"pigz -dc {local_path}/run_logs.tar.gz |sudo  tar xf - ")


def tear_down_docker(host):
    host.SshDirect.connect()
    remove_proxy_container(host.SshDirect)


def tear_down_dockers(hosts):
    for name, host in hosts:
        logging.info(f"[{name}: {host}] tearing down")
        tear_down_docker(host)
        logging.info(f"[{name}: {host}] success tearing down")

