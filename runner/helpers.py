import socket
import time

from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException, SSHException

from infra.model import base_config
from infra.plugins.ssh import SSHCalledProcessError


def hardware_config(hardware):
    def wrapper(func):
        func.__hardware_reqs = hardware
        return func
    return wrapper


def runner(tests):
    conf = base_config.init_base_config_obj()
    for _, test in tests.items():
        hardware_req = test.__config
        print(f"initializing hardware: {hardware_req}")
        time.sleep(3)
        print("done initializing hardware.. Running test..")
        test(conf)


def use_gravity_exec(connected_ssh_module):
    try:
        connected_ssh_module.execute("kubectl get po")
        return 'gravity exec'
    except SSHCalledProcessError:
        return ''


def deploy_proxy_container(connected_ssh_module, auth_args):
    # TODO: check if running instead of just trying to remove
    try:
        remove_proxy_container(connected_ssh_module)
    except:
        pass

    run_cmd = f'{use_gravity_exec(connected_ssh_module)} docker run -d --network=host --name=ssh_container orihab/ubuntu_ssh:1.1 {" ".join(auth_args)}'
    res = connected_ssh_module.execute(run_cmd)
    return res


def remove_proxy_container(connected_ssh_module):
    res = connected_ssh_module.execute(f'{use_gravity_exec(connected_ssh_module)} docker rm -f ssh_container')
    print(res)


def connect_via_running_docker(base):
    try:
        base.host.SSH.connect(base.host.SSH.TUNNEL_PORT)
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



def init_docker_and_connect(base):
    print("initializing docker")
    base.host.SSH.connect()
    docker_args = ['pem', base.host.user] if base.host.keyfile else ['password', base.host.user, base.host.password]
    deploy_proxy_container(base.host.SSH, docker_args)
    base.host.SSH.connect(base.host.SSH.TUNNEL_PORT)
    print("docker is running and ssh connected")


def tear_down_docker(base):
    print("tearing down docker")
    base.host.SSH.connect()
    remove_proxy_container(base.host.SSH)
    print("docker is stopped and disconnected")



# if __name__ == '__main__':
#     to_run = {k: v for k, v in locals().copy().items() if k.startswith('test')}
#     runner(to_run)
