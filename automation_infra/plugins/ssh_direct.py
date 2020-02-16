import os
import subprocess
from subprocess import CalledProcessError
import logging

from infra.model import plugins
from automation_infra.plugins import connection
from automation_infra.utils import snippet


class SshDirect(object):

    def __init__(self, host):
        self._host = host
        self._connection = None

    def connect(self, port=22, timeout=10):
        self._connection = connection.Connection(self._host, port)
        self._connection.connect(timeout)
        
    def get_transport(self):
        return self._connection._ssh_client.get_transport()

    def run_script(self, script, timeout=20 * 60):
        temp_ex = None
        try:
            return self._connection.run.script(script, output_timeout=timeout)
        except CalledProcessError as ex:
            temp_ex = ex
            logging.debug("Failed ssh cmd %(cmd)s %(output)s %(stderr)s", dict(cmd=script, output=temp_ex.output, stderr=temp_ex.stderr))
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def run_script_v2(self, script, timeout=20 * 60):
        """ This method will return subprocess.CompletedProcess object instead of stdout"""
        temp_ex = None
        try:
            return self._connection.run.script_v2(script, output_timeout=timeout)
        except CalledProcessError as ex:
            temp_ex = ex
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def execute(self, program, timeout=20 * 60):
        temp_ex = None
        try:
            completed_process = self._connection.run.execute(program, output_timeout=timeout)
            return completed_process.stdout
        except CalledProcessError as ex:
            temp_ex = ex
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def remote_hostname(self):
        return self.execute("echo $HOSTNAME").strip()

    def download_resource(self, remote_path, local_destination):
        full_bucket_path = f's3://anyvision-testing/{remote_path}'
        cmd = f"aws s3 cp {full_bucket_path} {local_destination}"
        self.execute(cmd)
        res = self.execute(f'ls {local_destination}')
        assert os.path.basename(remote_path) in res

    def run_parallel(self, scripts, max_jobs=None):
        temp_ex = None
        try:
            return self._connection.run.parallel(scripts, max_jobs=max_jobs)
        except CalledProcessError as ex:
            temp_ex = ex
            raise SSHCalledProcessError(temp_ex.returncode, temp_ex.cmd, temp_ex.output, temp_ex.stderr, self._host)

    def run_background_parallel(self, scripts, max_jobs=None):
        return self._connection.run.background_parallel(scripts, max_jobs=max_jobs)

    def run_background_script(self, script):
        return self._connection.run.background_script(script)

    def daemonize(self, command):
        return self._connection.run.background_script(command)

    def put(self, filenames, remotedir):
        filenames = filenames if isinstance(filenames, (list, tuple)) else (filenames, )
        return self._connection.put(filenames, remotedir)

    def put_contents(self, contents, remote_path):
        return self._connection.put_contents(contents, remote_path)

    def append_contents(self, contents, remote_path):
        return self._connection.append_contents(contents, remote_path)

    def get_contents(self, remote_path):
        return self._connection.get_contents(remote_path)

    def disconnect(self):
        self._connection.close()

    def run_snippet(self, code_snippet, *args, **kwargs):
        code = snippet.Snippet(code_snippet)
        code.prepare()
        instance = code.create_instance(self._host)
        return instance.run(*args, **kwargs)

    def run_background_snippet(self, code_snippet, *args, **kwargs):
        code = snippet.Snippet(code_snippet)
        code.prepare()
        instance = code.create_instance(self._host)
        return instance.run_background(*args, **kwargs)

    def _install_private_key(self, keyfile, install_to_host):
        filepath = install_to_host.mktemp(suffix=".pem")
        with open(keyfile) as f:
            key = f.read()
            install_to_host.ssh.put_contents(key, filepath)
            install_to_host.ssh.run_script("chmod 600 %s" % filepath)
        return filepath

    def copy_to(self, source_file_or_dir, dest_host, dest_file_or_dir):
        """ This method will copy from self._host to dest_host the source to
            dest folder specified
        """
        if dest_host.keyfile:
            key_path_on_source = self._install_private_key(dest_host.keyfile, self._host)
            prefix = "scp -i %s" % key_path_on_source
        else:
            prefix = "sshpass -p %s scp" % dest_host.password

        scp_script = '%(prefix)s -q  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no\
                     -r %(source)s root@%(dest_ip)s:%(dest)s' % dict(prefix=prefix,
                                                                     source=source_file_or_dir,
                                                                     dest_ip=dest_host.ip,
                                                                     dest=dest_file_or_dir)
        return self.run_script(scp_script)

    def upload(self, src, dest):
        """ will copy src files and folders to dest dir on self._host """
        if self._host.keyfile:
            prefix = "scp -i %s" % self._host.keyfile
        else:
            prefix = "sshpass -p %s scp" % self._host.password

        cmd_template = '%(prefix)s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no\
                        -r %(localpath)s %(username)s@%(hostname)s:%(remotepath)s'
        cmd = cmd_template % dict(prefix=prefix,
                                  localpath=src,
                                  username=self._host.user,
                                  hostname=self._host.ip,
                                  remotepath=dest)
        subprocess.check_call(cmd, shell=True)

    def download(self, localdir, *remote_pathes):
        if self._host.keyfile:
            prefix = "scp -i %s" % self._host.keyfile
        else:
            prefix = "sshpass -p %s scp" % self._host.password

        cmd_template = '%(prefix)s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no\
                        -r %(username)s@%(hostname)s:%(remotepath)s %(localpath)s'
        for dest_path in remote_pathes:
            cmd = cmd_template % dict(prefix=prefix,
                                      username=self._host.user,
                                      hostname=self._host.ip,
                                      remotepath=dest_path,
                                      localpath=localdir)
            subprocess.check_call(cmd, shell=True)


class SSHCalledProcessError(CalledProcessError):
    def __init__(self, returncode, cmd, output=None, stderr=None, host=None):
        super(SSHCalledProcessError, self).__init__(returncode, cmd, output, stderr)
        self.host = host

    def __str__(self):
        return "Command '%s' on host %s returned non-zero exit status %d\nstdout: %s\nstderr: %s" % \
               (self.cmd, self.host.alias, self.returncode, self.output, self.stderr)


plugins.register('SshDirect', SshDirect)
