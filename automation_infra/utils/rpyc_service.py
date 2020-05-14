import os
import logging
import sys
import signal
import subprocess
from rpyc.utils.server import ThreadedServer


def start_service(port, loglevel, pid_file, service):
    if os.path.exists(pid_file):
        raise Exception("Already running")

    ch = logging.StreamHandler(sys.stdout)
    logging.basicConfig(level=loglevel, format='%(relativeCreated)6d %(threadName)s %(message)s', handlers=[ch])
    server = ThreadedServer(service, hostname="0.0.0.0", port=port, protocol_config={"allow_public_attrs": True})
    with open(pid_file, 'w') as f:
        pid = "%d" % os.getpid()
        f.write(pid)
    server.start()


def _kill_process(pid):
    pids_to_kill = [pid]
    try:
        cmd = ["ps", "-o", "pid", "--no-headers", "--ppid", pid]
        child_pids += [int(p) for p in subprocess.check_output(cmd).decode("ascii").split()]
    except:
        logging.info("No child processes found for pid %d", pid)

    for p in pids_to_kill:
        os.kill(p, signal.SIGKILL)


def kill(pid_file):
    if not os.path.exists(pid_file):
        raise Exception("PID file not found: %s" % pid_file)

    with open(pid_file, 'r') as f:
        pid = int(f.read())

    _kill_process(pid)
    os.unlink(pid_file)
