import os, logging, os.path
from os import path
from automation_infra.plugins.ssh_direct import SshDirect
from infra.model import plugins


class Logs(object):
    def __init__(self, host):
        self._host = host
        self._logs_directory_path = '/tmp/logs'
        self._system_log_path = '/var/log/'
        self._docker_log_path = '/storage/logs/'
        self._system_compress_file_name = 'system_logs'
        self._docker_compress_file_name = 'docker_logs'
        self.create_logs_directory()

    def download_all_logs(self):
        self.download_system_logs()
        self.download_docker_logs()

    def download_docker_logs(self):
        self._host.SshDirect.remote_directory_exists(self._docker_log_path)
        compress_file_path = self.compress_log(self._docker_log_path, self._docker_compress_file_name)
        self._download_to_local(compress_file_path)
        self.decompress_log(compress_file_path)

    def download_system_logs(self):
        compress_file_path = self.compress_log(self._system_log_path, self._system_compress_file_name)
        self._download_to_local(compress_file_path)
        self.decompress_log(compress_file_path)

    def download_log_by_path(self, log_path, file_name):
        compress_file_path = self.compress_log(log_path, file_name)
        self._download_to_local(compress_file_path)
        self.decompress_log(compress_file_path)

    def _download_to_local(self, compress_file_path):
        self._host.SshDirect.download(self._logs_directory_path, compress_file_path)
        self._host.SshDirect.remote_file_exists(compress_file_path)

    def create_logs_directory(self):
        if not os.path.exists(self._logs_directory_path):
            try:
                os.mkdir(self._logs_directory_path)
                os.system(f" mkdir -m 777 {self._logs_directory_path}")
            except OSError:
                logging.error(f"Creation of the directory {self._logs_directory_path} failed")
        else:
            os.system(f"sudo chmod 777 {self._logs_directory_path}")

        self._host.SshDirect.execute(
            f"if [ ! -d {self._logs_directory_path} ]; then mkdir -m 777 {self._logs_directory_path}; else sudo chmod 777 {self._logs_directory_path}; fi")

    def compress_log(self, folder_to_compress, compress_file_name):
        compress_file = f"{self._logs_directory_path}/{compress_file_name}.tar.gz"
        self._host.SshDirect.execute(f"tar cf - {folder_to_compress} | pigz > {compress_file}")
        self._host.SshDirect.remote_file_exists(compress_file)
        logging.info(f"The docker logs compress in remote ---> {self._logs_directory_path}")
        return compress_file

    def decompress_log(self, file_to_decompress):
        os.chdir(self._logs_directory_path)
        assert os.system(f"pigz -dc {file_to_decompress} |sudo  tar xf - ") == 0
        logging.info(f"The docker logs decompress in local ---> {self._logs_directory_path} ")
        return file_to_decompress


plugins.register('Logs', Logs)
