import paramiko
import time

import os
from automation_infra.plugins import run
import glob


class Connection(object):

    def __init__(self, host, port=22, **kwargs):
        assert (host.keyfile or host.password) and not (host.keyfile and host.password)
        self._ip = host.ip
        self._username = host.user
        self._password = host.password
        self._keyfile = host.keyfile
        self._port = port
        self._ssh_client = None

    @property
    def run(self):
        return run.Run(self._ssh_client)

    def _files_to_upload(self, filenames):
        all_files = []
        for f in filenames:
            f = f if os.path.isabs(f) else os.path.join(os.path.abspath(os.path.curdir), f)
            all_files.extend(glob.glob(f))
        assert all_files, "No files to upload: " + ",".join(filenames)
        return set(all_files)

    def put(self, filenames, remotedir):
        file_pathes = self._files_to_upload(filenames)

        with self._ssh_client.open_sftp() as sftp:
            for filename in file_pathes:
                remote = remotedir + "/" + os.path.basename(filename)
                sftp.put(filename, remote)
                sftp.chmod(remote, os.stat(filename).st_mode)

    def _write_contents(self, contents, remote_path, file_mode):
        with self._ssh_client.open_sftp() as sftp:
            BLOCK_SIZE = 128 * 1024
            with sftp.file(remote_path, mode=file_mode) as f:
                for i in range(0, len(contents), BLOCK_SIZE):
                    f.write(contents[i: i + BLOCK_SIZE])

    def put_contents(self, contents, remote_path):
        self._write_contents(contents, remote_path, "wb")

    def append_contents(self, contents, remote_path):
        self._write_contents(contents, remote_path, "ab+")

    def get_contents(self, remote_path):
        # TODO: the is unnecessary bc it already exists in ssh.py, no?
        with self._ssh_client.open_sftp() as sftp:
            with sftp.file(remote_path, mode="r") as f:
                return f.read()

    def get(self, remotepath, localpath):
        with self._ssh_client.open_sftp() as sftp:
            sftp.get(remotepath, localpath)

    def close(self):
        self._ssh_client.close()
        self._ssh_client = None

    def _credentials(self):
        if self._password:
            return dict(password=self._password)

        return dict(key_filename=self._keyfile)

    def _try_connect(self, timeout, credentials):
        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.known_hosts = None
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh_client.connect(
            hostname=self._ip, port=self._port,
            username=self._username,
            look_for_keys=False, allow_agent=False,
            timeout=timeout,
            auth_timeout=60,
            ** credentials)

    def _specify_very_large_rekey_interval(self):
        '''This tries to workaround issue described in
           https://github.com/paramiko/paramiko/issues/822
        '''
        transport = self._ssh_client.get_transport()
        transport.packetizer.REKEY_PACKETS = pow(2, 64)
        transport.packetizer.REKEY_BYTES = pow(2, 64)

    def connect(self, timeout=10):
        begin = time.time()
        credentials = self._credentials()
        while True:
            try:
                self._try_connect(3, credentials)
                self._ssh_client.get_transport().set_keepalive(15)
                self._specify_very_large_rekey_interval()
                return
            except:
                if time.time() - begin < timeout:
                    time.sleep(0.1)
                    continue
                raise
