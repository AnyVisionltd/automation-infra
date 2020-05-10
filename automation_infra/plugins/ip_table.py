from infra.model import plugins


class Iptables(object):
    AUTOMATION_CHAIN = 'AUTOMATION-INFRA'

    def __init__(self, host):
        self._host = host
        self._ssh = host.SSH

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
        commands = [(f"iptables --check OUTPUT --jump {chain}", f"iptables --insert OUTPUT --jump {chain}"),
                    (f"iptables --check {chain} --jump RETURN", f"iptables --insert {chain} --jump RETURN")]
        for try_cmd, except_cmd in commands:
            try:
                self._host.SSH.execute(try_cmd)
            except:
                self._host.SSH.execute(except_cmd)

    def block(self, service_name):
        self._host.SSH.execute(f"iptables --insert {self.AUTOMATION_CHAIN} --dest {service_name} -j REJECT")

    def unblock(self, service_name):
        self._host.SSH.execute(f"iptables --delete {self.AUTOMATION_CHAIN} --dest {service_name} -j REJECT")

    def reset_state(self):
        self.flush_or_create()
        self.activate_automation_chain()


plugins.register('Iptables', Iptables)
