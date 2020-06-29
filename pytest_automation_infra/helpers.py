import logging
import time
import yaml
import paramiko

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
import os

from automation_infra.utils import waiter

logging.getLogger('paramiko').setLevel(logging.WARN)


def hardware_config(hardware, grouping=None):
    def wrapper(func):
        func.__hardware_reqs = hardware
        func.__cluster_config = grouping
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

    logging.debug("deploying proxy pod in k8s")
    connected_ssh_module.put('./docker_build/daemonset.yaml', '/tmp/')
    connected_ssh_module.execute("kubectl apply -f /tmp/daemonset.yaml")
    waiter.wait_nothrow(lambda: connected_ssh_module.execute("kubectl wait --for=condition=ready --timeout=1s pod -l app=automation-proxy"), timeout=60)
    logging.debug("success deploying proxy pod in k8s!")


def set_up_docker_container(connected_ssh_module):
    removed = remove_proxy_container(connected_ssh_module)
    if removed:
        logging.warning("Unexpected behavior: removed proxy container despite that I shouldn't have needed to")
    do_docker_login(connected_ssh_module)

    logging.debug("pulling docker")
    connected_ssh_module.execute(f"docker pull gcr.io/anyvision-training/automation-proxy:master")

    logging.debug("running docker")
    run_cmd = f'{use_gravity_exec(connected_ssh_module)} docker run -d --rm ' \
              f'--volume=/tmp/automation_infra/:/tmp/automation_infra ' \
              f'--volume=/etc/hosts:/etc/hosts '\
              f'--privileged ' \
              f'--network=host ' \
              f'--name=automation_proxy gcr.io/anyvision-training/automation-proxy:master'
    assert not connected_ssh_module.execute("docker ps -aq --filter 'name=automation_proxy'"), \
        "you want to run automation_proxy but it already exists, please remove it beforehand!"
    try:
        connected_ssh_module.execute(run_cmd)
    except SSHCalledProcessError as e:
        if "endpoint with name automation_proxy already exists in network host" in e.stderr:
            connected_ssh_module.execute("docker network disconnect --force host automation_proxy")
            connected_ssh_module.execute(run_cmd)
        else:
            raise e
    logging.debug("docker is running")


def deploy_proxy_container(connected_ssh_module):
    if is_k8s(connected_ssh_module):
        set_up_k8s_pod(connected_ssh_module)
    else:
        set_up_docker_container(connected_ssh_module)


def is_blank(connected_ssh_module):
    if not is_k8s(connected_ssh_module):
        try:
            connected_ssh_module.execute("docker ps")
        except SSHCalledProcessError:
            logging.warning("Didn't find docker or k8s on machine, "
                            "running infra on blank machine without proxy container. "
                            "All tests will fail unless docker/k8s is installed from within the test.")
            return True
    return False


def check_for_legacy_containers(ssh):
    if is_k8s(ssh):
        return
    container_names = ssh.execute("docker ps | awk '{print $NF}' | grep compose || true ").split()
    if not container_names:
        return
    common_prefix = os.path.commonprefix(container_names)
    if not common_prefix or common_prefix[-1] not in '_-':
        raise Exception(f"Found containers with different prefixes: {container_names}. "
                        f"Please prune accordingly and rerun test.")


def init_proxy_container_and_connect(host):
    logging.debug(f"[{host}] connecting to ssh directly")
    host.SshDirect.connect()
    logging.debug(f"[{host}] connected successfully")

    if is_blank(host.SshDirect):
        return
    check_for_legacy_containers(host.SshDirect)
    deploy_proxy_container(host.SshDirect)

    logging.debug(f"[{host}] connecting to ssh container")
    waiter.wait_nothrow(lambda: host.SSH.connect(port=host.tunnelport), timeout=60)
    logging.debug(f"[{host}] connected successfully")


def init_proxy_containers_and_connect(hosts):
    for name, host in hosts:
        logging.debug(f"[{name}: {host}] initializing machine ")
        init_proxy_container_and_connect(host)
        logging.debug(f"[{name}: {host}] success initializing docker and connecting to it")


def restart_proxy_container(host):
    if is_k8s(host.SshDirect):
        try:
            host.SshDirect.execute("kubectl delete po automation_proxy")
        except SSHCalledProcessError as e:
            if 'not found' in e.stderr:
                deploy_proxy_container(host.SshDirect)
    else:
        remove_proxy_container(host.SshDirect)
        waiter.wait_for_predicate(lambda: not host.SshDirect.execute("docker ps -aq --filter 'name=automation_proxy'"))
        deploy_proxy_container(host.SshDirect)
    waiter.wait_nothrow(host.SSH.connect, timeout=30)


def remove_proxy_container(connected_ssh_module):
    if is_k8s(connected_ssh_module):
        logging.debug("trying to remove k8s proxy pod")
        try:
            connected_ssh_module.execute("kubectl delete --force --grace-period=0 -f /tmp/daemonset.yaml")
        except SSHCalledProcessError:
            logging.debug(f"caught expected exception error when deleting /tmp/daemonset.yaml: daemonsets.apps automation-proxy not found")
    else:
        try:
            logging.debug("trying to remove docker container")
            connected_ssh_module.execute(f'{use_gravity_exec(connected_ssh_module)} docker kill automation_proxy')
            waiter.wait_for_predicate(lambda: not connected_ssh_module.execute("docker ps -aq --filter 'name=automation_proxy'"))
            logging.debug("removed successfully!")
            return True
        except SSHCalledProcessError as e:
            if ('No such container' in e.stderr) or ('is not running' in e.stderr):
                pass
            else:
                raise e
            logging.debug("nothing to remove")


def tear_down_container(host):
    if not is_blank(host.SshDirect):
        remove_proxy_container(host.SshDirect)


def tear_down_proxy_containers(hosts):
    for name, host in hosts:
        logging.debug(f"[{name}: {host}] tearing down")
        tear_down_container(host)
        logging.debug(f"[{name}: {host}] success tearing down")

