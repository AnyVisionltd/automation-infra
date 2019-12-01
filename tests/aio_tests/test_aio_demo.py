import os
import time

import logging

from runner.helpers import hardware_config


# These are all example tests:
@hardware_config(hardware={"type": "aio"})
def test_ssh(base_config):
    logging.warning("Running ssh test!")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.host.SSH.put('/tmp/temp.txt', '/tmp')
    logging.warning("put file!")
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    logging.warning("sleeping..")
    time.sleep(1)
    logging.warning("woke up !")
    assert 'temp.txt' not in res.split()


@hardware_config(hardware={"type": "aio"})
def test_ssh2(base_config):
    logging.warning("Running ssh test2!")
    time.sleep(1)
    os.system("echo this is a test > /tmp/temp2.txt")
    base_config.host.SSH.put('/tmp/temp2.txt', '/tmp')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp2.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp2.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    time.sleep(1)
    assert 'temp2.txt' not in res.split()
