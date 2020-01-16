import time
import logging
import signal


class Background(object):

    def __init__(self, run, command, pid_file, output_file, err_file, status_filename):
        self.run = run
        self.command = command
        self._out = output_file
        self._err = err_file
        self._status = status_filename
        self._pid_file = pid_file
        self._pid = None

    @property
    def pid(self):
        if self._pid is None:
            self._pid = self._get_pid(self._pid_file)
        return self._pid

    def _get_pid(self, pid_file, wait_pid_timeout=2):
        start = None
        while True:
            try:
                return int(self.run.execute('cat %s' % pid_file, 10).stdout.strip())
            except:
                start = start or time.time()
                if time.time() - start > wait_pid_timeout:
                    logging.error("wait for pid timedout!")
                    return None
                time.sleep(0.1)

    def _child_processes(self):
        assert self.pid is not None
        return self.run.execute("pgrep -P %d -d ' ' || true" % self.pid).stdout.strip()

    def kill(self, signum=signal.SIGKILL, timeout=60):
        if self.pid is None:
            raise Exception("Process is not running yet")
        try:
            children = self._child_processes()
            cmd = 'kill -%d -- %d %s' % (signum, self.pid, children)
            self.run.execute(cmd, timeout)
        except:
            if self.running():
                raise

    @property
    def output(self):
        return self.run.execute("cat %s 2>/dev/null || true" % self._out).stdout.strip()

    @property
    def error(self):
        return self.run.execute("cat %s 2>/dev/null || true" % self._err).stdout.strip()

    @property
    def returncode(self):
        if self.running():
            return None
        try:
            return int(self.run.execute("cat %s" % self._status).stdout.strip())
        except:
            # In case that script was aborted or terminated
            return -1

    def running(self):
        try:
            self.run.execute("kill -s 0 %s" % self.pid)
            return True
        except:
            return False

    def wait(self, timeout=10.0, interval=1.0):
        start = time.time()
        while True:
            try:
                if not self.running():
                    return
            except:
                if timeout and time.time() - start > timeout:
                    raise TimeoutError("Process %d is still active after %f secods" % (self.pid, timeout))
            logging.debug("Process %d is still active", self.pid)
            if interval:
                time.sleep(interval)
