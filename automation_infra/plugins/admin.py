from infra.model import plugins

class Admin(object):

    def __init__(self, host):
        self._host = host

    def flush_journal(self):
        self._host.SshDirect.execute("sudo journalctl --vacuum-time=1s")

    def log_to_journal(self, msg):
        cmd = f"echo '{msg}' | systemd-cat -t TESTING -p info"
        self._host.SshDirect.execute(cmd)

    def set_timezone(self, timezone):
        cmd = f"sudo timedatectl set-timezone {timezone}"
        self._host.SshDirect.execute(cmd)

    def machine_id(self):
        return self._host.SshDirect.execute('sudo cat /sys/class/dmi/id/product_uuid').strip()

    def exists(self, path):
        try:
            self._host.SshDirect.execute(f'ls {path}')
            return True
        except:
            return False


plugins.register('Admin', Admin)
