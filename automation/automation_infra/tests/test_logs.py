import os
import subprocess
from pytest_automation_infra.helpers import hardware_config
from automation_infra.plugins.logs import Logs

@hardware_config(hardware={"host": {'gpu':1}})
def test_logs(base_config):
     logs_plugin = base_config.hosts.host.Logs
     logs_plugin.download_docker_logs()
     logs_plugin.download_system_logs()
     logs_plugin.download_log_by_path("/home/*/.bashrc","user_.bashrc_log.txt")



@hardware_config(hardware={"host": {'gpu':2}})
def test_create_log_and_download(base_config):
    logs_plugin = base_config.hosts.host.Logs
    host = base_config.hosts.host
    logs_plugin.create_logs_directory()
    host.SshDirect.remote_directory_exists('/tmp/logs/')
    host.SshDirect.execute("touch /tmp/logs/test_log.txt")
    host.SshDirect.remote_file_exists('/tmp/logs/test_log.txt')
    host.SshDirect.execute("echo 'This is test log...' > /tmp/logs/test_log.txt")
    host.SshDirect.execute("echo 'Lets check that its work!' >> /tmp/logs/test_log.txt")
    compress_file = logs_plugin.compress_log('/tmp/logs/test_log.txt', 'compress_test_log.txt' )
    host.SshDirect.remote_file_exists(compress_file)
    host.SshDirect.download(f"/tmp/logs/", f"{compress_file}")
    os.path.exists(compress_file)
    logs_plugin.decompress_log('/tmp/logs/compress_test_log.txt.tar.gz')
    assert ('Lets check that its work!' == subprocess.getoutput("tail -1 /tmp/logs/tmp/logs/test_log.txt"))





