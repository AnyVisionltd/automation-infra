from pprint import pprint

from functools import wraps
import time


def hardware_config(cluster):
    print("\nsetting up test hardware")
    print(f"cluster:")
    pprint(cluster)
    time.sleep(1)
    def wrapper(func):
        @wraps(func)
        def wrapped(base_config, setup_only):
            print(f"running setup_only: {setup_only}")
            if not setup_only:
                func(base_config, setup_only)
            else:
                print("did setup only, didnt run test")
        return wrapped
    return wrapper


@hardware_config(cluster={"host1": {"ram": 10, "host_type": "virtual"}, "host2": {"gpu": (1,), "gpu_type": "1080Ti"}})
def test_host_construction(base_config, setup_only):
    print(f"args received: {base_config}")
    base_config.cluster.hosts.host2.test = 'host2test'
    base_config.mistake.field = 'mistakeField'
    assert base_config.cluster.hosts.host2.test == 'host2test'
    assert base_config.mistake.field == 'mistakeField'
    assert base_config.alias == 'config1'
    assert base_config.cluster.hosts.host1.Host.alias == 'monster'
