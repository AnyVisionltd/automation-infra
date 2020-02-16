import os
import zipfile
import modulefinder
import distutils.sysconfig as sysconfig
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class PythonPacker(object):

    def __init__(self):
        self.outfile = None
        self.dependencies = []

    @classmethod
    def from_file(cls, filepath, outfile=None):
        packer = cls()
        with open(filepath, 'r') as fp:
            packer._pack(fp, fp.read(), outfile)
        return packer

    @classmethod
    def from_script(cls, script, outfile):
        packer = cls()
        packer._pack(StringIO(script), script, outfile)
        return packer

    def _pack(self, buf, script, outfile):
        self._set_outfile_path(buf, outfile)
        with zipfile.ZipFile(self.outfile, 'w') as zp:
            zp.writestr('__main__.py', script)
            for module in self._modules_from_buffer(buf):
                zp.write(module.__file__, self._get_archive_path(module))
                self.dependencies.append(module.__name__)

    def _set_outfile_path(self, buf, outfile):
        if not outfile:
            outfile = buf.name
        name, suffix = os.path.splitext(outfile)
        if suffix != '.egg':
            outfile = name + '.egg'
        self.outfile = outfile

    def _modules_from_buffer(self, buf):
        finder = modulefinder.ModuleFinder()
        finder.load_module('__main__', buf, '__main__.py', ('', 'r', 1))
        stdlib = sysconfig.get_python_lib(standard_lib=True)
        for module in finder.modules.values():
            if module.__file__ is None:
                continue
            elif module.__file__ == '__main__.py':
                continue
            elif module.__name__ in self.dependencies:
                continue
            elif module.__file__.startswith(stdlib):
                self.dependencies.append(module.__name__)
                continue
            yield module

    @staticmethod
    def _get_archive_path(module):
        relative_name = module.__name__.replace('.', os.sep)
        return module.__file__[module.__file__.find(relative_name):]


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser('python packer')
    parser.add_argument('--script', type=str, help='script lines')
    parser.add_argument('--filepath', type=str, help='input script file path')
    parser.add_argument('--outfile', type=str, help='output archive path')
    args = parser.parse_args()

    if args.outfile:
        args.outfile = os.path.abspath(args.outfile)

    if args.filepath:
        args.filepath = os.path.abspath(args.filepath)
        if os.path.isdir(args.filepath):
            args.filepath = os.path.join(args.filepath, '__main__.py')
        PythonPacker.from_file(args.filepath)

    elif args.script:
        PythonPacker.from_script(args.script, args.outfile)

    else:
        parser.print_help()
