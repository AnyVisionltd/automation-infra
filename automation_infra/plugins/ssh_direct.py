import os
import shlex
import subprocess
from subprocess import CalledProcessError
import logging

from infra.model import plugins
from automation_infra.plugins import connection
from automation_infra.utils import snippet
import tempfile

from infra.utils import pem_key


class SshDirect(object):

    def __init__(self, host):
        self._host = host
        self._connection = None
        self.home_dir = '/home/' + self._host.user if self._host.user != 'root' else '/root'

    @property
    def connection(self):
        if self._connection is None:
            self.connect()
        return self._connection

    @property
    def ssh_string(self):
        return f"sshpass -p {self.connection.password} ssh -o StrictHostKeyChecking=no {self.connection._username}@{self.connection._ip} -p {self.connection.port}"

    def get_ip(self):
        return self._host.ip

    def connect(self, timeout=10):
        self._connection = connection.Connection(self._host)
        self._connection.connect(timeout)

    def get_transport(self):
        return self.connection._ssh_client.get_transport()

    def run_script(self, script, timeout=20 * 60):
        temp_ex = None
        try:
            return self.connection.run.script(script, output_timeout=timeout)
        except CalledProcessError as ex:
            temp_ex = ex
            logging.debug("Failed ssh cmd %(cmd)s %(output)s %(stderr)s", dict(cmd=script, output=temp_ex.output, stderr=temp_ex.stderr))
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def run_script_v2(self, script, timeout=20 * 60):
        """ This method will return subprocess.CompletedProcess object instead of stdout"""
        temp_ex = None
        try:
            return self.connection.run.script_v2(script, output_timeout=timeout)
        except CalledProcessError as ex:
            temp_ex = ex
            logging.error(temp_ex.stderr)
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def execute(self, program, timeout=20 * 60):
        temp_ex = None
        try:
            completed_process = self.connection.run.execute(program, output_timeout=timeout)
            return completed_process.stdout
        except CalledProcessError as ex:
            temp_ex = ex
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)


    def remote_hostname(self):
        return self.execute("echo $HOSTNAME").strip()


    def run_parallel(self, scripts, max_jobs=None):
        temp_ex = None
        try:
            return self.connection.run.parallel(scripts, max_jobs=max_jobs)
        except CalledProcessError as ex:
            temp_ex = ex
            logging.error(temp_ex.stderr)
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def run_background_parallel(self, scripts, max_jobs=None):
        return self.connection.run.background_parallel(scripts, max_jobs=max_jobs)

    def run_background_script(self, script):
        return self.connection.run.background_script(script)

    def daemonize(self, command):
        return self.connection.run.background_script(command)

    def put(self, filenames, remotedir):
        filenames = filenames if isinstance(filenames, (list, tuple)) else (filenames, )
        return self.connection.put(filenames, remotedir)

    def put_contents(self, contents, remote_path):
        return self.connection.put_contents(contents, remote_path)

    def put_content_from_fileobj(self, file_object, remote_path):
        return self.connection.put_contents_from_fileobj(file_object, remote_path)

    def append_contents(self, contents, remote_path):
        return self.connection.append_contents(contents, remote_path)

    def get_contents(self, remote_path):
        return self.connection.get_contents(remote_path)

    def disconnect(self):
        self.connection.close()

    def run_snippet(self, code_snippet, *args, **kwargs):
        excludes = kwargs.pop('excludes', [])
        code = snippet.Snippet(self._host, code_snippet, excludes)
        with tempfile.NamedTemporaryFile(prefix="snippet") as f:
            code.prepare(f.name)
            instance = code.create_instance(self)
        return instance.run(*args, **kwargs)

    def run_background_snippet(self, code_snippet, *args, **kwargs):
        excludes = kwargs.pop('excludes', [])
        code = snippet.Snippet(self._host, code_snippet, excludes)
        with tempfile.NamedTemporaryFile(prefix="snippet") as f:
            code.prepare(f.name)
        instance = code.create_instance(self)
        return instance.run_background(*args, **kwargs)

    def _install_private_key(self, keyfile, install_to_host):
        filepath = install_to_host.mktemp(suffix=".pem")
        with open(keyfile) as f:
            key = f.read()
            install_to_host.ssh.put_contents(key, filepath)
            install_to_host.ssh.run_script("chmod 600 %s" % filepath)
        return filepath

    @property
    def _using_keyfile(self):
        return self._host.keyfile or self._host.pkey

    def copy_to(self, source_file_or_dir, dest_host, dest_file_or_dir):
        """ This method will copy from self._host to dest_host the source to
            dest folder specified
        """
        if dest_host.keyfile:
            key_path_on_source = self._install_private_key(dest_host.keyfile, self._host)
            prefix = "scp -i %s" % key_path_on_source
        else:
            prefix = "sshpass -p '%s' scp -o PubkeyAuthentication=no" % dest_host.password

        scp_script = '%(prefix)s -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no\
                     -r %(source)s root@%(dest_ip)s:%(dest)s' % dict(prefix=prefix,
                                                                     source=source_file_or_dir,
                                                                     dest_ip=dest_host.ip,
                                                                     dest=dest_file_or_dir)
        return self.run_script(scp_script)

    def upload(self, src, dest):
        """ will copy src files and folders to dest dir on self._host """
        if self._using_keyfile:
            if self._host.keyfile:
                prefix = "scp -i %s" % self._host.keyfile
            else:
                prefix = "scp "
        else:
            prefix = "sshpass -p '%s' scp -P %d -o PubkeyAuthentication=no" % (self._connection.password, self._connection.port)

        cmd_template = '%(prefix)s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR\
                        -r %(localpath)s %(username)s@%(hostname)s:%(remotepath)s'
        cmd = cmd_template % dict(prefix=prefix,
                                  localpath=src,
                                  username=self._connection._username,
                                  hostname=self._host.ip,
                                  remotepath=dest)
        subprocess.check_call(cmd, shell=True)

    def download(self, localdir, *remote_pathes):
        if self._using_keyfile:
            if self._host.keyfile:
                prefix = "scp -T -i %s" % self._host.keyfile
            else:
                prefix = "scp "
        else:
            prefix = "sshpass -p '%s' scp -T -P %d -o PubkeyAuthentication=no" % (self._connection.password, self._connection.port)

        cmd_template = '%(prefix)s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR\
                        -r %(username)s@%(hostname)s:%(remotepath)s %(localpath)s'
        for dest_path in remote_pathes:
            cmd = cmd_template % dict(prefix=prefix,
                                      username=self._connection._username,
                                      hostname=self._host.ip,
                                      remotepath=dest_path,
                                      localpath=localdir)
            try:
                subprocess.check_call(cmd, shell=True)
            except:
                logging.exception(f"exception trying to download {dest_path} with command: {cmd}")

    def rsync(self, src, dst, exclude_dirs=None):
        if self._using_keyfile:
            raise NotImplementedError("Rsync with SSH key is not yet implemented")
        exclude_dirs = exclude_dirs or []
        exclude_expr = " ".join([f"--exclude {exclude_dir}" for exclude_dir in exclude_dirs])
        prefix = f"sshpass -p {self._connection.password} rsync -ravh --delete {exclude_expr} -e \"ssh -p {self._connection.port} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR\""
        cmd = f"{prefix} {src} {self._connection._username}@{self._host.ip}:{dst}"
        subprocess.check_output(cmd, shell=True)

    def compress(self, src, dst):
        src = src if type(src) is list else [src]
        dst = dst if dst.endswith('tar.gz') else '{dst}.tar.gz'
        try:
            self.execute(f"tar --warning=no-file-changed --use-compress-program=pigz -cvf {dst} {' '.join([shlex.quote(folder) for folder in src])}")
        except SSHCalledProcessError as e:
            if e.returncode == 1:
                logging.info("compress should have succeeded, the return code is 1 only because 'some files differ'")
                logging.info(f"ls on dest dir: {self.execute(f'ls -al {os.path.dirname(dst)}')}")
            else:
                raise



class SSHCalledProcessError(CalledProcessError):
    def __init__(self, returncode, cmd, output=None, stderr=None, host=None):
        super(SSHCalledProcessError, self).__init__(returncode, cmd, output, stderr)
        self.host = host

    def __str__(self):
        return "Command '%s' on host %s returned non-zero exit status %d\nstdout: %s\nstderr: %s" % \
               (self.cmd, self.host.ip, self.returncode, self.output, self.stderr)


plugins.register('SshDirect', SshDirect)
