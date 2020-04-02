import logging
import time

import paramiko

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
import os

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
        connected_ssh_module.execute("kubectl get po")
        return True
    except SSHCalledProcessError:
        return False


def do_docker_login(connected_ssh_module):
    logging.debug("doing docker login")
    remote_home = connected_ssh_module.execute("echo $HOME").strip()
    try:
        config_exists = connected_ssh_module.execute(f"ls {remote_home}/.docker/config.json")
    except SSHCalledProcessError as e:
        if 'No such file or directory' in e.stderr:
            connected_ssh_module.execute(f"mkdir -p {remote_home}/.docker")
            connected_ssh_module.put(f"{os.getenv('HOME')}/.docker/config.json", f"{remote_home}/.docker/")
        else:
            raise e
    connected_ssh_module.execute("docker login https://gcr.io")


def create_secret(connected_ssh_module):
    logging.debug("creating ImagePullSecret")
    do_docker_login(connected_ssh_module)  # This is necessary to put the config.json file
    remote_home = connected_ssh_module.execute("echo $HOME").strip()
    connected_ssh_module.execute(
        f"kubectl create secret generic imagepullsecret --from-file=.dockerconfigjson={remote_home}/.docker/config.json --type=kubernetes.io/dockerconfigjson"
    )


def set_up_k8s_pod(connected_ssh_module):
    remove_proxy_container(connected_ssh_module)
    running = connected_ssh_module.execute(
        """
        if [[ $(kubectl cluster-info) == *'Kubernetes master'*'running'* ]]; 
        then echo "running";  
            else ""; 
        fi;
        """)
    if not running:
        raise Exception("K8s not running!")

    try:
        connected_ssh_module.execute("kubectl get secrets imagepullsecret")
    except:
        create_secret(connected_ssh_module)

    logging.info("deploying proxy pod in k8s")
    connected_ssh_module.put('./docker_build/daemonset.yaml', '/tmp/')
    connected_ssh_module.execute("kubectl apply -f /tmp/daemonset.yaml")
    logging.info("success deploying proxy pod in k8s!")


def set_up_docker_container(connected_ssh_module):
    removed = remove_proxy_container(connected_ssh_module)
    if removed:
        logging.warning("Unexpected behavior: removed proxy container despite that I shouldn't have needed to")
    do_docker_login(connected_ssh_module)

    logging.info("initializing docker")
    run_cmd = f'{use_gravity_exec(connected_ssh_module)} docker run -d --rm ' \
              f'--volume=/tmp/automation_infra/ ' \
              f'--privileged ' \
              f'--network=host ' \
              f'--name=automation_proxy gcr.io/anyvision-training/automation-proxy:master'
    connected_ssh_module.execute(run_cmd)
    logging.info("docker is running")


def deploy_proxy_container(connected_ssh_module):
    if is_k8s(connected_ssh_module):
        set_up_k8s_pod(connected_ssh_module)
    else:
        set_up_docker_container(connected_ssh_module)


def init_proxy_container_and_connect(host):
    logging.info(f"[{host}] connecting to ssh directly")
    host.SshDirect.connect()
    logging.info(f"[{host}] connected successfully")

    deploy_proxy_container(host.SshDirect)

    logging.info(f"[{host}] connecting to ssh container")
    for i in range(15):
        # Need this because the kubectl run daemonset returns when the container is starting
        # but sometimes can take a few seconds for the container to be running....
        try:
            host.SSH.connect(port=host.tunnelport)
            break
        except paramiko.ssh_exception.NoValidConnectionsError:
            logging.debug(f"ssh connect attempt {i}: no valid connections to {host.ip}")
            time.sleep(1)
    logging.info(f"[{host}] connected successfully")


def init_proxy_containers_and_connect(hosts):
    for name, host in hosts:
        logging.info(f"[{name}: {host}] initializing machine ")
        init_proxy_container_and_connect(host)
        logging.info(f"[{name}: {host}] success initializing docker and connecting to it")


def remove_proxy_container(connected_ssh_module):
    if is_k8s(connected_ssh_module):
        logging.info("trying to remove k8s proxy pod")
        try:
            connected_ssh_module.execute("kubectl delete -f /tmp/daemonset.yaml")
        except SSHCalledProcessError:
            logging.info(f"caught expected exception error when deleting /tmp/daemonset.yaml: daemonsets.apps automation-proxy not found")
    else:
        try:
            logging.info("trying to remove docker container")
            connected_ssh_module.execute(f'{use_gravity_exec(connected_ssh_module)} docker rm -f automation_proxy')
            logging.info("removed successfully!")
            return True
        except SSHCalledProcessError as e:
            if ('No such container' not in e.stderr) and ('No such container' not in e.stdout):
                raise e
            logging.info("nothing to remove")


def tear_down_container(host):
    host.SshDirect.connect()
    remove_proxy_container(host.SshDirect)


def tear_down_proxy_containers(hosts):
    for name, host in hosts:
        logging.info(f"[{name}: {host}] tearing down")
        tear_down_container(host)
        logging.info(f"[{name}: {host}] success tearing down")

