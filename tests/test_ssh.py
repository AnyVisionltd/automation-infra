import logging
import os
import time

import pytest

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {"gpu": 1, "ram": 16}, "host2": {}})
def test_ssh(base_config):
    logging.info(f"PID of test_Ssh: {os.getpid()}")
    logging.info(f"Running ssh test on host {base_config.hosts.host.ip}")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.hosts.host.SSH.put('/tmp/temp.txt', '/tmp')
    logging.info("put file!")
    res = base_config.hosts.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.hosts.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.hosts.host.SSH.execute('ls /tmp')
    logging.info("sleeping..")
    time.sleep(1)
    logging.info("woke up !")
    assert 'temp.txt' not in res.split()
    time.sleep(1)
    #assert False


if __name__ == '__main__':
    # These can be run via pytest or like this too:
    pytest.main(args=['.', ], plugins=[])
