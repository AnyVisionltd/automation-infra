import os
import time

import logging

from runner.helpers import hardware_config


# These are all example tests:
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


@hardware_config(hardware={"type": "ori_vm"})
def test_ssh2(base_config):
    logging.info(f"Running ssh2 test on host {base_config.host.ip}")
    time.sleep(1)
    os.system("echo this is a test > /tmp/temp2.txt")
    base_config.host.SSH.put('/tmp/temp2.txt', '/tmp')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp2.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp2.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    time.sleep(1)
    assert 'temp2.txt' not in res.split()
