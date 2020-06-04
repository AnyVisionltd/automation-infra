import os
import sys
import distutils.sysconfig as sysconfig

from zipfile import ZipFile
from modulefinder import ModuleFinder

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class PythonPacker(object):

    def __init__(self, buffer, outfile, excludes=()):
        if not hasattr(buffer, 'name') or not buffer.name:
            raise ValueError('buffer must have a name attr')
        self.buffer = buffer
        self.excludes = excludes
        self.outfile = outfile
        self._validate_outfile_path()
        self.rootdir = os.path.dirname(self.buffer.name)
        self.rootdir += os.sep
        self.modules = set()
        self.badmodules = set()

    def _validate_outfile_path(self):
        if not self.outfile:
            self.outfile = self.buffer.name
        name, suffix = os.path.splitext(self.outfile)
        if suffix != '.egg':
            self.outfile = name + '.egg'

    @classmethod
    def from_file(cls, filepath, outfile=None, excludes=()):
        with open(filepath, 'r') as fp:
            packer = cls(fp, outfile, excludes)
            packer.pack()
        return packer

    @classmethod
    def from_script(cls, script, outfile, filename=None, excludes=()):
        buffer = StringIO(script)
        if filename is None:
            curdir = os.path.abspath(os.path.curdir)
            filename = os.path.join(curdir, '__main__.py')
        buffer.name = filename
        packer = cls(buffer, outfile, excludes)
        packer.pack()
        return packer

    def pack(self):
        with ZipFile(self.outfile, 'w') as zp:
            zp.writestr('__main__.py', self.buffer.read())
            self.buffer.seek(0)
            self._archive_buffer(zp, self.buffer)

    def _archive_buffer(self, zp, buffer):
        for module in self._modules_from_buffer(buffer):
            arcpath = self._get_module_archpath(module)
            if arcpath == '__main__.py':
                continue
            if module.__file__.startswith(self.rootdir):
                with open(module.__file__) as fp:
                    self._archive_buffer(zp, fp)
            zp.write(module.__file__, arcpath)

    def _modules_from_buffer(self, buffer):
        finder = ModuleFinder(excludes=self.excludes)
        bufdir = os.path.dirname(buffer.name)
        sys.path.insert(0, bufdir)
        try:
            finder.load_module('__main__', buffer, '__main__.py', ('', 'r', 1))
        finally:
            sys.path.remove(bufdir)
        self.badmodules.update(finder.badmodules.keys())
        stdlib = sysconfig.get_python_lib(standard_lib=True)
        stdlib_local = sysconfig.get_python_lib(standard_lib=True, prefix='/usr/local')
        dist_packages = sysconfig.get_python_lib()
        for module in finder.modules.values():
            if module.__file__ is None:
                continue
            elif module.__file__.startswith(stdlib):
                continue
            elif module.__file__.startswith(stdlib_local):
                continue
            elif module.__file__.startswith(dist_packages):
                continue
            elif module.__file__ == buffer.name:
                continue
            elif module.__file__ == '__main__.py':
                continue
            elif module.__file__ in self.modules:
                continue
            self.modules.add(module.__file__)
            yield module

    def _get_module_archpath(self, module):
        if module.__file__.startswith(self.rootdir):
            return self._truncated_module_path(module)
        relpath = module.__name__.replace('.', os.sep)
        return module.__file__[module.__file__.find(relpath):]

    def _truncated_module_path(self, module):
        path = module.__file__[len(self.rootdir):]
        if path.startswith('automation/'):
            path = path[len('automation/'):]
        return path


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser('python packer')
    parser.add_argument(
        '-s', '--script',
        type=str,
        help='script lines'
    )
    parser.add_argument(
        '-f', '--filepath',
        type=str,
        help='input script file path'
    )
    parser.add_argument(
        '-o', '--outfile',
        type=str,
        help='output archive path'
    )
    parser.add_argument(
        '-e', '--excludes',
        nargs='*',
        type=str,
        help='modules names to exclude'
    )
    args = parser.parse_args()

    if args.outfile:
        args.outfile = os.path.abspath(args.outfile)

    if args.script:
        PythonPacker.from_script(
            args.script,
            args.outfile,
            args.filepath,
            args.excludes
        )

    elif args.filepath:
        args.filepath = os.path.abspath(args.filepath)
        if os.path.isdir(args.filepath):
            args.filepath = os.path.join(args.filepath, '__main__.py')
        PythonPacker.from_file(args.filepath, args.outfile, args.excludes)

    else:
        parser.print_help()
