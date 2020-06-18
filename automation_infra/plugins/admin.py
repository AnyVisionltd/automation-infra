from infra.model import plugins

class Admin(object):

    def __init__(self, host):
        self._host = host

    def flush_journal(self):
        self._host.SshDirect.execute("sudo journalctl --vacuum-time=1s")


plugins.register('Admin', Admin)
