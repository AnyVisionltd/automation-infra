import logging
import os
import time
import io

from automation_infra.plugins.admin import Admin

from pytest_automation_infra.helpers import hardware_config


installer = "ssh"


def _test_fileobj_upload(host):
    string_obj = io.StringIO("sasha king")
    host.SshDirect.put_content_from_fileobj(string_obj, "/tmp/test_obj/file")
    content_to_verify = host.SshDirect.get_contents("/tmp/test_obj/file")
    assert content_to_verify == b"sasha king"
    logging.info("Uploading content from fileobj to existing dir")
    string_obj = io.StringIO("sasha king")
    host.SshDirect.put_content_from_fileobj(string_obj, "/tmp/test_obj/file2")
    content_to_verify = host.SshDirect.get_contents("/tmp/test_obj/file2")
    assert content_to_verify == b"sasha king"
    logging.info("Testing very large content of 1MB")
    large_content = "s" * 1024 * 1024
    content = io.StringIO(large_content)
    host.SshDirect.put_content_from_fileobj(content, "/tmp/test_obj/large_content")
    content_to_verify = host.SshDirect.get_contents("/tmp/test_obj/large_content").decode()
    assert content_to_verify == large_content

def _test_upload_download(host):
    os.system("echo this is a test > /tmp/temp.txt")
    host.SshDirect.upload('/tmp/temp.txt', '/tmp/test_upload.txt')
    host.SshDirect.download('/tmp/test_download.txt', '/tmp/test_upload.txt')
    with open('/tmp/test_download.txt', 'r') as f:
        contents = f.read().strip()
    assert contents == 'this is a test'


def _test_rsync_ssh(host, host_ssh):
    logging.info("create some files")
    os.system("mkdir -p /tmp/rsync/1 /tmp/rsync/2")
    os.system('echo "file 1" > /tmp/rsync/1/file')
    os.system('echo "file 2" > /tmp/rsync/2/file')

    logging.info("rsync")
    sync_dir = host.mktemp()
    while host.Admin.exists(sync_dir):
        sync_dir = host.mktemp()
    host_ssh.rsync('/tmp/rsync', sync_dir)
    files = host_ssh.execute(f'find {sync_dir}/rsync/ -type f').split()
    assert set(files) == set([f'{sync_dir}/rsync/1/file', f'{sync_dir}/rsync/2/file'])

    logging.info("add one more file")
    os.system('echo "file 3" > /tmp/rsync/2/file3')
    host_ssh.rsync('/tmp/rsync', sync_dir)
    files = host_ssh.execute(f'find {sync_dir}/rsync/ -type f').split()
    assert set(files) == set([f'{sync_dir}/rsync/1/file', f'{sync_dir}/rsync/2/file', f'{sync_dir}/rsync/2/file3'])

    logging.info("Delete a file on sorce")
    os.system('rm /tmp/rsync/2/file3')
    host_ssh.rsync('/tmp/rsync', sync_dir)
    files = host_ssh.execute(f'find {sync_dir}/rsync/ -type f').split()
    assert set(files) == set([f'{sync_dir}/rsync/1/file', f'{sync_dir}/rsync/2/file'])


@hardware_config(hardware={"host": {}})
def test_ssh(base_config):
    logging.info(f"PID of test_Ssh: {os.getpid()}")
    logging.info(f"Running ssh test on host {base_config.hosts.host.ip}")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.hosts.host.SshDirect.put('/tmp/temp.txt', '/tmp')
    base_config.hosts.host.SshDirect.upload('/tmp/temp.txt', '/tmp')
    logging.info("put file!")
    res = base_config.hosts.host.SshDirect.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.hosts.host.SshDirect.execute('rm /tmp/temp.txt')
    res = base_config.hosts.host.SshDirect.execute('ls /tmp')
    logging.info("sleeping..")
    time.sleep(1)
    logging.info("woke up !")
    assert 'temp.txt' not in res.split()
    time.sleep(1)
    logging.info("Uploading content from fileobj")
    _test_fileobj_upload(base_config.hosts.host)
    logging.info("Testing upload and download of files")
    _test_upload_download(base_config.hosts.host)
    logging.info("Test rsync on ssh direct")
    host = base_config.hosts.host
    try:
        _test_rsync_ssh(host, host.SshDirect)
    except NotImplementedError:
        logging.warning("rsync not implemented on key_file auth")
    logging.info("Test rsync on ssh")
