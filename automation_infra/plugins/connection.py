import paramiko
import time

import os
from automation_infra.plugins import run
import glob


class Connection(object):

    def __init__(self, host, **kwargs):
        self._ip = host.ip
        self._username = host.user
        self.password = host.password
        self._keyfile = host.keyfile
        self._pkey = host.pkey
        self.port = host.port
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

    @staticmethod
    def _mkdir_p(sftp, remote_directory):
        dir_path = str()
        for dir_folder in remote_directory.split("/"):
            if dir_folder == "":
                continue
            dir_path += r"/{0}".format(dir_folder)
            try:
                sftp.listdir(dir_path)
            except IOError:
                sftp.mkdir(dir_path)

    def put_contents_from_fileobj(self, file_obj, remote_path):
        remote_dir = os.path.dirname(remote_path)
        with self._ssh_client.open_sftp() as sftp:
            Connection._mkdir_p(sftp, remote_dir)
            BLOCK_SIZE = 128 * 1024
            with sftp.file(remote_path, mode="wb") as f:
                while True:
                    buffer = file_obj.read(BLOCK_SIZE)
                    if not buffer:
                        break
                    f.write(buffer)

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

    def _credentials(self):
        if self.password:
            return dict(password=self.password)

        return dict(key_filename=self._keyfile,
                    pkey=self._pkey)

    def _try_connect(self, timeout, credentials):
        self._ssh_client.known_hosts = None
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh_client.connect(
            hostname=self._ip, port=self.port,
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
        self._ssh_client = paramiko.SSHClient()
        while True:
            try:
                self._try_connect(3, credentials)
                self._ssh_client.get_transport().set_keepalive(15)
                self._specify_very_large_rekey_interval()
                return
            except:
                self.close()
                if time.time() - begin < timeout:
                    time.sleep(0.1)
                    continue
                raise
