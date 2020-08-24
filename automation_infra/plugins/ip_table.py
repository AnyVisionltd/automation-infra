from infra.model import plugins


class Iptables(object):
    AUTOMATION_CHAIN = 'AUTOMATION-INFRA'

    def __init__(self, host):
        self._host = host
        self._ssh = host.SshDirect

    def flush(self):
        self._ssh.execute(f'sudo iptables --flush {self.AUTOMATION_CHAIN}')

    def create(self):
        self._ssh.execute(f"sudo iptables  --new-chain {self.AUTOMATION_CHAIN}")

    def flush_or_create(self):
        try:
            self.flush()
        except:
            self.create()

    def activate_automation_chain(self):
        chain = self.AUTOMATION_CHAIN
        commands = [(f"sudo iptables  -w --check OUTPUT --jump {chain}", f"sudo iptables  --insert OUTPUT --jump {chain}"),
                    (f"sudo iptables  -w --check FORWARD --jump {chain}", f"sudo iptables  --insert FORWARD --jump {chain}"),
                    (f"sudo iptables  -w --check {chain} --jump RETURN", f"sudo iptables  --insert {chain} --jump RETURN")]
        for try_cmd, except_cmd in commands:
            try:
                self._ssh.execute(try_cmd)
            except:
                self._ssh.execute(except_cmd)

    def block(self, service_name):
        self._ssh.execute(f"sudo iptables  -w --insert {self.AUTOMATION_CHAIN} --dest {service_name} -j REJECT")

    def unblock(self, service_name):
        self._ssh.execute(f"sudo iptables  -w --delete {self.AUTOMATION_CHAIN} --dest {service_name} -j REJECT")

    def drop(self, service_name, protocol=None):
        protocol_cmd = self.protocol_cmd(protocol)
        self._ssh.execute(f"sudo iptables -w -I FORWARD {protocol_cmd} --dest {service_name} -j DROP")

    def undrop(self, service_name, protocol=None):
        protocol_cmd = self.protocol_cmd(protocol)
        self._ssh.execute(f"sudo iptables -w -D FORWARD {protocol_cmd} --dest {service_name} -j DROP")

    @staticmethod
    def protocol_cmd(protocol):
        return f"-p {protocol}" if protocol else ""

    def reset_state(self):
        self.flush_or_create()
        self.activate_automation_chain()


plugins.register('Iptables', Iptables)
