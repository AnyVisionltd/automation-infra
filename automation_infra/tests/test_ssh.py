import logging
import os
import time

import pytest

from pytest_automation_infra.helpers import hardware_config
from .snippet_test_functions import get_pyobject, use_external_lib, send_class, catch_exception, background_task
from .snippet_test_functions import Person


@hardware_config(hardware={"host": {}})
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


@hardware_config(hardware={'host': {}})
@pytest.mark.parametrize('target, args, kwargs, expected, run_background', (
        (get_pyobject, (5,), {}, lambda x: x == get_pyobject(5), False),
        (use_external_lib, (), {'uri': 'http://google.com'}, lambda x: x == use_external_lib('http://google.com'), False),
        (send_class, (), {'person': Person('david'), 'name': 'moshe'}, lambda x: x.name == 'moshe', False),
        (catch_exception, (RuntimeError,), {}, lambda x: type(x) is RuntimeError, False),
        (background_task, (), {}, lambda x: x is True, True)
))
def test_snippet(base_config, target, args, kwargs, expected, run_background):
    ssh = base_config.hosts.host.SSH
    try:
        if run_background:
            background = ssh.run_background_snippet(target, *args, **kwargs)
            result = background.wait_result()
        else:
            result = ssh.run_snippet(target, *args, **kwargs)

    except Exception as e:
        assert expected(e), str(e)

    else:
        assert expected(result), str(result)
