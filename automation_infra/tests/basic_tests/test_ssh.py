import logging
import os
import time
import io

from pytest_automation_infra.helpers import hardware_config

def _test_fileobj_upload(host):
    string_obj = io.StringIO("sasha king")
    host.SSH.put_content_from_fileobj(string_obj, "/tmp/test_obj/file")
    content_to_verify = host.SSH.get_contents("/tmp/test_obj/file")
    assert content_to_verify == b"sasha king"
    logging.info("Uploading content from fileobj to existing dir")
    string_obj = io.StringIO("sasha king")
    host.SSH.put_content_from_fileobj(string_obj, "/tmp/test_obj/file2")
    content_to_verify = host.SSH.get_contents("/tmp/test_obj/file2")
    assert content_to_verify == b"sasha king"
    logging.info("Testing very large content of 1MB")
    large_content = "s" * 1024 * 1024
    content = io.StringIO(large_content)
    host.SSH.put_content_from_fileobj(content, "/tmp/test_obj/large_content")
    content_to_verify = host.SSH.get_contents("/tmp/test_obj/large_content").decode()
    assert content_to_verify == large_content

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
    logging.info("Uploading content from fileobj")
    _test_fileobj_upload(base_config.hosts.host)