import tempfile
import yaml
from infra.utils import shell
import os
import logging

class CloudInit(object):

    def __init__(self, run_qcow_path):
        self.iso_base_path = run_qcow_path

    def _write_metadata(self, vm, filepath):
        with open(filepath, 'w') as f:
            f.write("instance-id: %s\n" % vm.name)
            f.write("local-hostname: %s\n" % vm.name)

    def _write_userdata(self, vm, filepath):
        mounts = []
        for disk in vm.disks:
            disk_uuid = disk.get('serial', None)
            mount_point = disk.get('mount', None)
            fs = disk.get('fs', None)
            if disk_uuid and mount_point and fs:
                mounts.append([f"UUID={disk_uuid}", mount_point, fs, "defaults", "0", "0"])

        data = {"preserve_hostname": False,
                "hostname": vm.name,
                "output" : {"all": ">> /var/log/cloud-init.log"},
                "ssh_pwauth": "yes",
                "mounts" : mounts}

        with open(filepath, 'w') as f:
            f.write("#cloud-config\n")
            yaml.dump(data, f)

    def _iso_path(self, vm):
        return os.path.join(self.iso_base_path, "%s_%s.iso" % (vm.name, vm.uuid))

    def generate_iso(self, vm):
        iso_path = self._iso_path(vm)
        logging.debug(f"Generating iso for vm {vm.name} iso: {vm.cloud_init_iso}")
        with tempfile.TemporaryDirectory() as tmpdir:
            user_data = os.path.join(tmpdir, "user-data")
            meta_data = os.path.join(tmpdir, "meta-data")
            self._write_metadata(vm, meta_data)
            self._write_userdata(vm, user_data)
            cmd = f"mkisofs -o {iso_path} -V cidata -J -r {user_data} {meta_data}"
            shell.run_cmd(cmd)
        return iso_path

    def delete_iso(self, vm):
        iso_path = self._iso_path(vm)
        os.remove(iso_path)
