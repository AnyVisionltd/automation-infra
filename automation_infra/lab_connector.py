import munch
from IPython.core.magic_arguments import (
    argument, magic_arguments, parse_argstring)
from IPython.core.magic import magics_class, line_magic, Magics, line_cell_magic
import pytest_automation_infra


@magics_class
class LabConnector(Magics):

    @magic_arguments()
    @argument('path', help="Hardware yaml path")
    @line_cell_magic
    def hardware_attach(self, line):
        args = parse_argstring(self.hardware_attach, line)
        hardware_yaml = args.path
        hardware = {'machines' : pytest_automation_infra.get_local_config(hardware_yaml)}

        base = munch.DefaultMunch(munch.Munch)
        base.hosts = munch.Munch()
        pytest_automation_infra.init_hosts(hardware, base)
        self.shell.user_ns['base'] = base
        self._reconnect()

    def _reconnect(self):
        base = self.shell.user_ns['base']
        for host in base.hosts.values():
            host.SshDirect.connect()

    @line_magic
    def reconnect(self, _):
        self._reconnect()


def load_ipython_extension(ipython):
    ipython.register_magics(LabConnector)
