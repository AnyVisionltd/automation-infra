from IPython.terminal.ipapp import TerminalIPythonApp
from IPython.core.getipython import get_ipython
from automation_infra.plugins import ssh_direct


class AnyTerminalIPythonApp(TerminalIPythonApp):

    def __init__(self):
        super(AnyTerminalIPythonApp, self).__init__()
        self.extensions.append('automation_infra.lab_connector')

    @classmethod
    def launch_instance(cls, argv=None, **kwargs):
        app = cls.instance(**kwargs)
        app.initialize(argv)

        def my_handler(shell, _, value, __, tb_offset):
            if shell.call_pdb:
                get_ipython().showtraceback(running_compiled_code=True)

        get_ipython().set_custom_exc((ssh_direct.SSHCalledProcessError,), my_handler)
        app.start()

    def init_banner(self):
        self.shell.banner1 = "Anyvision Test terminal"
        super().init_banner()


launch_new_instance = AnyTerminalIPythonApp.launch_instance

if __name__ == "__main__":
    launch_new_instance()

