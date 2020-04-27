from contextlib import contextmanager
from infra.utils import shell, filesystem
import os
import glob
import threading
from infra.utils import waiter
import logging


class NBDProvisioner(object):

    _DEVICES = "/dev/nbd*"

    def __init__(self):
        self.device_search_lock = threading.Lock()

    def _find_free_device(self):

        def _is_used(device_path):
            class_path = "/sys/class/block/%s/size" % os.path.basename(device_path)
            with open(class_path, 'r') as f:
                device_size = f.read().strip()
                return device_size != "0"

        for device_path in self._list_devices():
            if not _is_used(device_path):
                return device_path
        return None

    def _disconnect_device(self, device_path):
        disconnect_cmd = ["qemu-nbd", "--disconnect", device_path]
        shell.run_cmd(disconnect_cmd)

    def _connect_device(self, device_path, image_path):
        connect_cmd = ["qemu-nbd", "--connect", device_path, image_path]
        shell.run_cmd(connect_cmd)

    def _list_devices(self):
        for path in glob.glob(NBDProvisioner._DEVICES):
            yield path

    def _allocate_and_connect(self, image_path):
        with self.device_search_lock:
            device = self._find_free_device()
            if device is None:
                raise Exception("No free device")
            logging.debug("Connecting %s to %s", image_path, device)
            self._connect_device(device, image_path)
            return device

    @contextmanager
    def _ndb_mount(self, image_path):
        logging.debug("Trying to mount %s", image_path)
        device = waiter.wait_for_predicate_nothrow(lambda: self._allocate_and_connect(image_path), timeout=10)
        try:
            yield device
        finally:
            logging.debug("Disconnecting %s from %s", image_path, device)
            self._disconnect_device(device)

    def _try_provision_device(self, image_path, fstype, disk_uuid):
        with self._ndb_mount(image_path) as device:
            logging.debug(f"Going to create fs {fstype} id {disk_uuid} on device {device}")
            cmd = filesystem.Mkfs.command(device, fstype, disk_uuid=disk_uuid)
            shell.run_cmd(cmd)

    def provision_disk(self, image_path, fstype, disk_uuid):
        self._try_provision_device(image_path, fstype, disk_uuid)
        logging.debug("Created filesystem on %s", image_path)

    def _free_nbd_devices(self):
        for path in self._list_devices():
            self._disconnect_device(path)

    def initialize(self):
        logging.info("Loading nbd driver required to mount qcow disks")
        shell.run_cmd("modprobe nbd max_part=8")
        self._free_nbd_devices()


if __name__ == '__main__':
    import argparse
    from infra.utils import anylogging
    parser = argparse.ArgumentParser()
    parser.add_argument("--fs", help="Filesystem type", required=False, default="ext4")
    parser.add_argument("--label", help="Label for the filesystem", required=False)
    parser.add_argument("image", help="Image path")

    args = parser.parse_args()
    anylogging.configure_logging(root_level=logging.DEBUG, console_level=logging.DEBUG)
    provisioner = NBDProvisioner()
    provisioner.initialize()
    provisioner.provision_disk(args.image, args.fs, args.label)
