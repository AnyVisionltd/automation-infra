import os
import base64

try:
    import cPickle as pickle
except ImportError:
    import pickle

from .pypacker import PythonPacker


class SnippetRunner(object):

    def __init__(self, snippet, ssh, interpreter, snippet_params_file_path):
        self.interpreter = interpreter
        self.snippet = snippet
        self.ssh = ssh
        self.script_path = None
        self.snippet_dir = '/tmp'
        self.snippet_params_file_path = snippet_params_file_path

    def run(self, *args, **kwargs):
        self.deploy(args, kwargs)
        cmd = '{0} {1}'.format(self.interpreter, self.script_path)
        result = self.ssh.run_script(cmd)
        return self._parse_result(result)

    def run_background(self, *args, **kwargs):
        self.deploy(args, kwargs)
        cmd = '{0} {1}'.format(self.interpreter, self.script_path)
        background = self.ssh.run_background_script(cmd)

        def wait_result(timeout=None):
            background.wait(timeout)
            if background.running():
                raise RuntimeError("script is still running")
            return self._parse_result(background.output)

        background.wait_result = wait_result
        return background

    def deploy(self, args, kwargs):
        if not self.snippet.archive_path:
            self.snippet.prepare()
        basename = os.path.basename(self.snippet.archive_path)
        self.script_path = os.path.join(self.snippet_dir, basename)
        self.ssh.put(self.snippet.archive_path, self.snippet_dir)

        self._prepare_params_file(args, kwargs)
        self.ssh.put(self.snippet_params_file_path, self.snippet_dir)

    def _prepare_params_file(self, args, kwargs):
        with open(self.snippet_params_file_path, 'wb') as f:
            pickle.dump((args, kwargs), f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _parse_result(result):
        success, output = pickle.loads(base64.b64decode(result))
        if not success:
            raise output
        return output


class Snippet(object):

    def __init__(self, host, target, excludes=()):
        self._host = host
        self.target = target
        self.excludes = excludes
        self.archive_path = None
        self.snippet_params_file_path = None

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
    with open('{params_file}', 'rb') as f:
        args, kwargs = pickle.load(f)
    res = {module}.{target}(*args, **kwargs)
except Exception as e:
    print_result(False, e)
else:
    print_result(True, res)
"""

    def prepare(self, outfile=None):
        module = self.target.__module__
        name = self.target.__name__
        self.snippet_params_file_path = self._host.mktemp(prefix=f'{name}_params', suffix='.pkl')
        script = self._wrapper_script.format(module=module, target=name, params_file=self.snippet_params_file_path)
        packed = PythonPacker.from_script(script, outfile or name, excludes=self.excludes)
        self.archive_path = packed.outfile

    def create_instance(self, host, interpreter='python3'):
        return SnippetRunner(self, host.SSH, interpreter, self.snippet_params_file_path)
