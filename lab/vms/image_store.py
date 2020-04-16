import os
import asyncio
import logging
import json
import time


class QcowException(Exception):
    pass


class ImageStore(object):

    def __init__(self, loop, base_qcow_path, run_qcow_path, ssd_path, hdd_path):
        self.loop = loop
        self.base_qcow_path = base_qcow_path
        self.run_qcow_path = run_qcow_path
        self.ssd_path = ssd_path
        self.hdd_path = hdd_path

    def run_qcow_path_from_name(self, vm_name):
        image_file_name = "%s_%s.qcow2" % (vm_name, str(time.time()))
        return os.path.abspath(os.path.join(self.run_qcow_path, image_file_name))

    def _storage_path(self, storage_type, vm_name, serial_num):
        base_path = self.ssd_path if storage_type == "ssd" else self.hdd_path
        file_name = "%s_%s_%s.qcow2" % (vm_name, storage_type, serial_num)
        return os.path.abspath(os.path.join(base_path, file_name))

    def base_qcow_path_from_name(self, image_label):
        image_name = '%s.qcow2' % image_label
        return os.path.abspath(os.path.join(self.base_qcow_path, image_name))

    async def list_images(self):
        files = await self.loop.run_in_executor(None,
                        lambda: os.listdir(os.path.abspath(self.base_qcow_path)))
        return [os.path.splitext(file)[0] for file in files]

    async def clone_qcow(self, base_qcow_image_name, image_name):
        # first check if file exists
        backing_file = self.base_qcow_path_from_name(base_qcow_image_name)

        # sadly io does not support is exists for files
        if not os.path.exists(backing_file):
            raise QcowException("Image %s does not exists", backing_file)

        path = self.run_qcow_path_from_name(image_name)

        args = ['qemu-img', 'create', '-f', 'qcow2', '-o', 'backing_file=%s' % backing_file, path]
        logging.debug("Running command %s", args)
        proc = await asyncio.create_subprocess_exec(*args, close_fds=True,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        returncode = await proc.wait()
        if returncode != 0:
            logging.debug("backing file = %(backing_file)s, outputfile = %(output_file)s, return code = %(returncode)s",
                          dict(backing_file=backing_file, output_file=path, returncode=returncode))
            out = await proc.stdout.read()
            raise QcowException("Failed clone qcow for label %s out: %s" % (base_qcow_image_name, out))
        return path

    async def create_qcow(self, vm_name, storage_type, size_gb, serial_num):
        path = self._storage_path(storage_type, vm_name, serial_num)
        size = "%dG" % int(size_gb)
        args = ['qemu-img', 'create', '-f', 'qcow2', path, size]
        logging.debug("Running command %s", args)
        proc = await asyncio.create_subprocess_exec(*args, close_fds=True,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        returncode = await proc.wait()
        if returncode != 0:
            out = await proc.stdout.read()
            raise QcowException("Failed create qcow for file %s out: %s" % (path, out))
        return path

    async def qcow_info(self, image_path):
        args = ['qemu-img', 'info', '-U', '--output=json', image_path]
        proc = await asyncio.create_subprocess_exec(*args, close_fds=True,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

        out, _ = await proc.communicate()
        return json.loads(out)

    async def delete_qcow(self, image_path):
        logging.debug("Remove Qcow file %s ", image_path)
        await self.loop.run_in_executor(None, lambda : os.remove(image_path))


if __name__ == '__main__':
    import argparse
    import pprint
    from infra.utils import anylogging
    anylogging.configure_logging(console_level=logging.DEBUG, file_level=logging.NOTSET)
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(title='command', dest="command")
    commands.required = True

    create = commands.add_parser('create', help="Create QCOW image with given base image")
    create.add_argument('--image')
    create.add_argument('--backing')
    create.add_argument('--size')
    create.add_argument('--type')
    create.add_argument('--name')

    delete = commands.add_parser('delete', help="Delete QCOW image")
    delete.add_argument('--image')

    info = commands.add_parser('info', help="Get QCOW image info")
    info.add_argument('--image')
    args = parser.parse_args()

    if args.command == 'create':
        backing_path = os.path.abspath(args.backing) if args.backing else None
        backing_dir = os.path.dirname(backing_path) if backing_path else None
        backing_file = os.path.basename(backing_path) if backing_path else None
    else:
        backing_dir = None
    run_abs_path = os.path.abspath(args.image)
    run_qcow_dir = os.path.dirname(run_abs_path)
    run_qcow_name = os.path.basename(run_abs_path)

    loop = asyncio.get_event_loop()
    store = ImageStore(loop, backing_dir, run_qcow_dir, run_qcow_dir, run_qcow_dir)
    if args.command == 'create':
        if args.backing is None:
            loop.run_until_complete(store.create_qcow(args.name, args.type, args.size, serial_num="1234"))
        else:
            loop.run_until_complete(store.clone_qcow(backing_file, run_qcow_name))
    elif args.command == 'delete':
        loop.run_until_complete(store.delete_qcow(backing_file, args.image))
    else:
        pprint.pprint(loop.run_until_complete(store.qcow_info(args.image)))
