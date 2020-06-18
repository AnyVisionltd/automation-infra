from infra.model import plugins


class Iptables(object):
    AUTOMATION_CHAIN = 'AUTOMATION-INFRA'

    def __init__(self, host):
        self._host = host
        self._ssh = host.SshDirect

    def flush(self):
        self._ssh.execute(f'iptables --flush {self.AUTOMATION_CHAIN}')

    def create(self):
        self._ssh.execute(f"iptables --new-chain {self.AUTOMATION_CHAIN}")

    def flush_or_create(self):
        try:
            self.flush()
        except:
            self.create()

    def activate_automation_chain(self):
        chain = self.AUTOMATION_CHAIN
        commands = [(f"iptables -w --check OUTPUT --jump {chain}", f"iptables --insert OUTPUT --jump {chain}"),
                    (f"iptables -w --check FORWARD --jump {chain}", f"iptables --insert FORWARD --jump {chain}"),
                    (f"iptables -w --check {chain} --jump RETURN", f"iptables --insert {chain} --jump RETURN")]
        for try_cmd, except_cmd in commands:
            try:
                self._ssh.execute(try_cmd)
            except:
                self._ssh.execute(except_cmd)

    def block(self, service_name):
        self._ssh.execute(f"iptables -w --insert {self.AUTOMATION_CHAIN} --dest {service_name} -j REJECT")

    def unblock(self, service_name):
        self._ssh.execute(f"iptables -w --delete {self.AUTOMATION_CHAIN} --dest {service_name} -j REJECT")

    def reset_state(self):
        self.flush_or_create()
        self.activate_automation_chain()


plugins.register('Iptables', Iptables)
