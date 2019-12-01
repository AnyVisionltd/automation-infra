import os
import time

import logging

from runner.helpers import hardware_config


# These are all example tests:
@hardware_config(hardware={"type": "aio"})
def test_ssh(base_config):
    logging.debug("Running ssh test!")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.host.SSH.put('/tmp/temp.txt', '/tmp')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    time.sleep(5)
    assert 'temp.txt' not in res.split()


@hardware_config(hardware={"type": "aio"})
def test_ssh2(base_config):
    logging.debug("Running ssh test2!")
    time.sleep(3)
    os.system("echo this is a test > /tmp/temp2.txt")
    base_config.host.SSH.put('/tmp/temp2.txt', '/tmp')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp2.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp2.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    time.sleep(5)
    assert 'temp2.txt' not in res.split()
