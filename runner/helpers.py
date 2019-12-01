import time

from infra.model import base_config
from runner import CONSTS


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


def deploy_proxy_container(connected_ssh_module, auth_args):
    # TODO: check if running instead of just trying to remove
    try:
        remove_proxy_container(connected_ssh_module)
    except:
        pass

    res = connected_ssh_module.execute('mkdir -p /tmp/build')
    res = connected_ssh_module.put('./runner/docker_build/Dockerfile', '/tmp/build')
    res = connected_ssh_module.put('./runner/docker_build/entrypoint.sh', '/tmp/build')

    image_tag = 'automation-tests:1.111'
    build_cmd = f'docker build -t {image_tag} /tmp/build'
    res = connected_ssh_module.execute(build_cmd)
    run_cmd = f'docker run -d --network=host --name=ssh_container {image_tag} {" ".join(auth_args)}'
    res = connected_ssh_module.execute(run_cmd)


def remove_proxy_container(connected_ssh_module):
    res = connected_ssh_module.execute(f'docker rm -f ssh_container')


def connect_via_running_docker(base):
    base.host.SSH.connect(CONSTS.TUNNEL_PORT)


def init_docker_and_connect(base):
    print("initializing docker")
    base.host.SSH.connect()
    docker_args = ['pem', base.host.user] if base.host.keyfile else ['password', base.host.user, base.host.password]
    deploy_proxy_container(base.host.SSH, docker_args)
    base.host.SSH.connect(CONSTS.TUNNEL_PORT)
    print("docker is running and ssh connected")


def tear_down_docker(base):
    print("tearing down docker")
    base.host.SSH.connect()
    remove_proxy_container(base.host.SSH)
    print("docker is stopped and disconnected")



# if __name__ == '__main__':
#     to_run = {k: v for k, v in locals().copy().items() if k.startswith('test')}
#     runner(to_run)
