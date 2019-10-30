import socket
import logging
from . import background
from . import parallel
import tempfile
import os
import subprocess
from subprocess import CalledProcessError
from subprocess import CompletedProcess


class Run(object):

    def __init__(self, ssh_client):
        self._ssh_client = ssh_client
        self._logger = logging.getLogger('ssh')

    def script(self, bash_script, output_timeout=20 * 60):
        return self.script_v2(bash_script, output_timeout).stdout

    def script_v2(self, bash_script, output_timeout=20 * 60):
        self._logger.debug("Running bash script:\n\n%(bash_script)s\n", dict(bash_script=bash_script))
        command = "\n".join([
            "sh << 'RACKATTACK_SSH_RUN_SCRIPT_EOF'",
            bash_script,
            "RACKATTACK_SSH_RUN_SCRIPT_EOF\n"])
        return self.execute(command, output_timeout)

    def execute(self, command, output_timeout=20 * 60):
        transport = self._ssh_client.get_transport()
        chan = transport.open_session()
        try:
            chan.exec_command(command)
            chan.settimeout(output_timeout)
            stdin = chan.makefile('wb', -1)
            stdout = chan.makefile('rb', -1)
            stderr = chan.makefile_stderr('rb', -1)
            stdin.close()
            output = self._read_output(stdout, output_timeout)
            status = chan.recv_exit_status()
            error = stderr.read().decode('utf-8')
            completed_process = subprocess.CompletedProcess(command, status)
            completed_process.stderr = error
            completed_process.stdout = output
            stdout.close()
            stderr.close()
            self._logger.debug("SSH Execution output:\n\n%(output)s\n", dict(output=output))
            if status != 0:
                raise CalledProcessError(completed_process.returncode,
                                         completed_process.args,
                                         completed_process.stdout,
                                         completed_process.stderr)
            return completed_process
        finally:
            chan.close()

    def _read_output(self, stdout, output_timeout):
        output_array = []
        try:
            while True:
                segment = stdout.read().decode('utf-8')
                if segment == "":
                    break
                output_array.append(segment)
        except socket.timeout:
            output = "".join(output_array)
            e = socket.timeout(
                "Timeout executing, no input for timeout of '%s'. Partial output was\n:%s" % (
                    output_timeout, output))
            e.output = output
            raise e
        return "".join(output_array)

    def _exec(self, command):
        transport = self._ssh_client.get_transport()
        chan = transport.open_session()
        try:
            chan.exec_command(command)
            status = chan.recv_exit_status()
            if status != 0:
                raise subprocess.CalledProcessError(status, command)
        finally:
            chan.close()

    def background_script(self, bash_script):
        random_base = tempfile.mktemp(prefix='background', dir='/tmp/')
        pid_filename = random_base + ".pid"
        out_filename = random_base + ".out"
        err_filename = random_base + ".err"
        status_filename = random_base + ".retcode"
        command = "\n".join([
            "nohup sh << 'RACKATTACK_SSH_RUN_SCRIPT_EOF' >& /dev/null &",
            "(%(bash_script)s 1>%(out)s 2>%(err)s& echo $!>%(pid)s;wait $!);echo $?>%(status)s" % dict(
                bash_script=bash_script,
                out=out_filename,
                err=err_filename,
                pid=pid_filename,
                status=status_filename),
            "RACKATTACK_SSH_RUN_SCRIPT_EOF\n"])
        try:
            self._exec(command)
        except CalledProcessError as e:
            raise Exception("Failed running '%s', status '%s'" % (bash_script, e.returncode))

        return background.Background(self, bash_script, pid_filename, out_filename, err_filename, status_filename)

    def _parallel_commands(self, base_dir, scripts, max_jobs, command_suffix=""):
        max_jobs = max_jobs or 0
        script_commands = ["((%(script)s 1>%(out)s 2>%(err)s& echo $!>%(pid)s;wait $!);echo $?>%(status)s)" %
                           dict(script=script,
                                out=parallel.Parallel.outfile(base_dir, i),
                                err=parallel.Parallel.errfile(base_dir, i),
                                status=parallel.Parallel.statusfile(base_dir, i),
                                pid=parallel.Parallel.pidfile(base_dir, i))
                           for i, script in enumerate(scripts)]
        joined_script_commands = "\n".join(script_commands)
        return "\n".join(["parallel --no-notice --jobs=%d << 'PARALLEL_SCRIPT' %s" % (max_jobs, command_suffix),
                          joined_script_commands,
                          "PARALLEL_SCRIPT\n"])

    def parallel(self, scripts, max_jobs=None, output_timeout=20 * 60):
        base_dir = tempfile.mktemp(dir='/tmp/')
        parallel_cmd = self._parallel_commands(base_dir, scripts, max_jobs)
        command = "\n".join(["mkdir %s" % base_dir, parallel_cmd])
        try:
            self.execute(command, output_timeout)
            return parallel.Parallel(self, scripts, base_dir)
        except Exception as e:
            e.args += ('When running bash script "%s"' % command),
            raise

    def background_parallel(self, scripts, max_jobs=None):
        base_dir = tempfile.mktemp(dir='/tmp/')

        pid_filename = os.path.join(base_dir, "parallel.pid")
        out_filename = os.path.join(base_dir, "parallel.out")
        err_filename = os.path.join(base_dir, "parallel.err")
        status_filename = os.path.join(base_dir, "parallel.status")
        parallel_cmd = self._parallel_commands(base_dir, scripts, max_jobs, " 1>%s 2>%s &" % (out_filename, err_filename))

        command = "\n".join(["mkdir %s" % base_dir,
                             "nohup sh << 'RACKATTACK_SSH_RUN_SCRIPT_EOF' >& /dev/null &",
                             "(%(bash_script)s echo $!>%(pid)s;wait $!);echo $?>%(status)s" % dict(
                                 bash_script=parallel_cmd,
                                 out=out_filename,
                                 err=err_filename,
                                 status=status_filename,
                                 pid=pid_filename),
                             "RACKATTACK_SSH_RUN_SCRIPT_EOF\n"])

        try:
            self._exec(command)
            return parallel.BackgroundParallel(self, scripts, base_dir, pid_filename, out_filename, err_filename, status_filename)
        except CalledProcessError as e:
            raise Exception("Failed running '%s', status '%s'" % (scripts, e.returncode))
