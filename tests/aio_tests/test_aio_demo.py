import os
import random
import time

from runner.helpers import hardware_config


# These are all example tests:
@hardware_config(hardware={"type": "aio"})
def test_ssh(base_config):
    print("Running ssh test!")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.host.SSH.put('/tmp/temp.txt', '/tmp')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' not in res.split()
