import logging
import socket
from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException, SSHException

from infra.plugins.ssh import SSHCalledProcessError


def init_logger():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)',
                        filename='output.log')


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
    # TODO: check if running instead of just trying to remove
    remove_proxy_container(connected_ssh_module)

    run_cmd = f'{use_gravity_exec(connected_ssh_module)} docker run -d --rm --network=host --name=ssh_container orihab/ubuntu_ssh:2.0 {" ".join(auth_args)}'
    res = connected_ssh_module.execute(run_cmd)
    return res


def remove_proxy_container(connected_ssh_module):
    try:
        connected_ssh_module.execute(f'{use_gravity_exec(connected_ssh_module)} docker rm -f ssh_container')
    except SSHCalledProcessError as e:
        if 'No such container' not in e.stderr:
            raise e


def connect_via_running_docker(base):
    try:
        base.host.SSH.docker_connect(base.host.SSH.TUNNEL_PORT)
        return
    except NoValidConnectionsError:
        print("no valid connections")
    except socket.timeout as e:
        print("socket timeout trying to connect via running docker")
    except AuthenticationException:
        print("Authentication failed")
    except SSHException:
        print("Error reading SSH protocol banner")
    except Exception as e:
        print(f"caught other exception: {e}")
    raise Exception("unsuccessful connecting via running docker...")


def init_docker(host):
    logging.info("initializing docker")
    host.SSH.connect()
    deploy_proxy_container(host.SSH)
    host.SSH.docker_connect(host.SSH.TUNNEL_PORT)
    logging.info("docker is running and ssh connected")


def init_dockers_and_connect(hosts):
    for name, host in hosts:
        init_docker(host)


def tear_down_docker(host):
    logging.info("tearing down docker")
    host.SSH.connect()
    remove_proxy_container(host.SSH)
    logging.info("docker is stopped and disconnected")


def tear_down_dockers(hosts):
    for name, host in hosts:
        tear_down_docker(host)
