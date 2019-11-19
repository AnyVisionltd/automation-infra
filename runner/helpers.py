import time

from infra.model import base_config


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


# if __name__ == '__main__':
#     to_run = {k: v for k, v in locals().copy().items() if k.startswith('test')}
#     runner(to_run)
