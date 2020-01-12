import logging
import os
import time

import pytest

from pytest_automation_infra.helpers import hardware_config


#@pytest.mark.timeout(30)
@hardware_config(hardware={"type": "ori_pem"})
def test_ssh(base_config):
    logging.info(f"Running ssh test on host {base_config.host.ip}")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.host.SSH.put('/tmp/temp.txt', '/tmp')
    logging.info("put file!")
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    logging.info("sleeping..")
    time.sleep(1)
    logging.info("woke up !")
    assert 'temp.txt' not in res.split()


if __name__ == '__main__':
    # These can be run via pytest or like this too:
    pytest.main(args=['.', ], plugins=[])
