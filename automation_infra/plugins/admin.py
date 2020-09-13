from infra.model import plugins

class Admin(object):

    def __init__(self, host):
        self._host = host

    def flush_journal(self):
        self._host.SshDirect.execute("sudo journalctl --vacuum-time=1s")

    def log_to_journal(self, msg):
        cmd = f"echo '{msg}' | systemd-cat -t TESTING -p info"
        self._host.SshDirect.execute(cmd)


plugins.register('Admin', Admin)
