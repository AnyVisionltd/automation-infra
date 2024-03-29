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


    def _filter(self, source_host, source_port, dest_host, dest_port):
        src_host = f"--src {source_host}" if source_host else ""
        src_port = f"--sport {source_port}" if source_port else ""
        dst_host = f"--dst {dest_host}" if dest_host else ""
        dst_port = f"--dport {dest_port}" if dest_port else ""
        return f"{src_host} {src_port} {dst_host} {dst_port}"




    def drop(self, service_name, protocol=None, service_port=None, source_service=None, source_port=None):
        protocol_cmd = self.protocol_cmd(protocol)
        iptables_filter = self._filter(source_service, source_port, service_name, service_port)
        cmd = f"sudo iptables -w --insert {self.AUTOMATION_CHAIN} {protocol_cmd} {iptables_filter} -j DROP"
        self._ssh.execute(cmd)

    def undrop(self, service_name, protocol=None, service_port=None, source_service=None, source_port=None):
        protocol_cmd = self.protocol_cmd(protocol)
        iptables_filter = self._filter(source_service, source_port, service_name, service_port)
        self._ssh.execute(f"sudo iptables -w --delete {self.AUTOMATION_CHAIN} {protocol_cmd} {iptables_filter} -j DROP")

    @staticmethod
    def protocol_cmd(protocol):
        return f"-p {protocol}" if protocol else ""

    def reset_state(self):
        self.flush_or_create()
        self.activate_automation_chain()


plugins.register('Iptables', Iptables)
