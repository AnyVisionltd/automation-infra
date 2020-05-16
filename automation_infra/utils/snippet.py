import os
import base64

try:
    import cPickle as pickle
except ImportError:
    import pickle

from .pypacker import PythonPacker


class SnippetRunner(object):

    def __init__(self, snippet, ssh, interpreter):
        self.interpreter = interpreter
        self.snippet = snippet
        self.ssh = ssh
        self.script_path = None

    def run(self, *args, **kwargs):
        self.deploy()
        params = self._prepare_input(args, kwargs)
        cmd = '{0} {1} {2}'.format(self.interpreter, self.script_path, params)
        result = self.ssh.run_script(cmd)
        return self._parse_result(result)

    def run_background(self, *args, **kwargs):
        self.deploy()
        params = self._prepare_input(args, kwargs)
        cmd = '{0} {1} {2}'.format(self.interpreter, self.script_path, params)
        background = self.ssh.run_background_script(cmd)

        def wait_result(timeout=None):
            background.wait(timeout)
            if background.running():
                raise RuntimeError("script is still running")
            return self._parse_result(background.output)

        def output():
            result = self.ssh.get_contents(background.remote_output_file)
            self._parse_result(result)

        background.wait_result = wait_result
        background.read_output = output
        return background

    def deploy(self):
        if not self.snippet.archive_path:
            self.snippet.prepare()
        basename = os.path.basename(self.snippet.archive_path)
        self.script_path = os.path.join('/tmp', basename)
        self.ssh.put(self.snippet.archive_path, '/tmp')

    @staticmethod
    def _prepare_input(args, kwargs):
        pickled_params = pickle.dumps((args, kwargs), pickle.HIGHEST_PROTOCOL)
        return base64.b64encode(pickled_params).decode().strip()

    @staticmethod
    def _parse_result(result):
        success, output = pickle.loads(base64.b64decode(result))
        if not success:
            raise output
        return output


class Snippet(object):

    def __init__(self, target, excludes=()):
        self.target = target
        self.excludes = excludes
        self.archive_path = None

    _wrapper_script = """
import sys
import os
import base64
try:
    import cPickle as pickle
except ImportError:
    import pickle

def print_result(success, result):
    output = pickle.dumps((success, result), protocol=pickle.HIGHEST_PROTOCOL)
    output = base64.b64encode(output).decode().strip()
    sys.stdout.write(output)
    sys.stdout.flush()
    exit(0)
    
try:
    import {module}
    if len(sys.argv) > 1:
        args, kwargs = pickle.loads(base64.b64decode(sys.argv[1]))
    else:
        args, kwargs = tuple(), dict()
    res = {module}.{target}(*args, **kwargs)
except Exception as e:
    print_result(False, e)
else:
    print_result(True, res)
"""

    def prepare(self, outfile=None):
        module = self.target.__module__
        name = self.target.__name__
        script = self._wrapper_script.format(module=module, target=name)
        packed = PythonPacker.from_script(script, outfile or name, excludes=self.excludes)
        self.archive_path = packed.outfile

    def create_instance(self, host, interpreter='python3'):
        return SnippetRunner(self, host.SSH, interpreter)
