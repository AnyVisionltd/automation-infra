import logging
import os
import time
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
import sys
import threading

from automation_infra.plugins.ssh_direct import SSHCalledProcessError

try:
    from devops_automation_infra.plugins.seaweed import Seaweed as BaseObject
except ImportError:
    from automation_infra.plugins.base_plugin import TunneledPlugin as BaseObject
from infra.model import plugins


class ResourceManager(BaseObject):
    def __init__(self, host):
        super().__init__(host)
        self._client = None

    def config_aws(self):
        if not os.path.exists(f'{os.path.expanduser("~")}/.aws'):
            raise FileNotFoundError("Missing aws credentials in ~/.aws folder")
        connected_ssh_module = self._host.SSH
        remote_home = connected_ssh_module.execute("echo $HOME").strip()
        try:
            config_exists = len(connected_ssh_module.execute(f"ls {remote_home}/.aws/c*")) == 2
        except SSHCalledProcessError as e:
            if 'No such file or directory' in e.stderr:
                connected_ssh_module.execute(f"mkdir -p {remote_home}/.aws")
                connected_ssh_module.put(f"{os.getenv('HOME')}/.aws/*", f"{remote_home}/.aws/")
            else:
                raise e
        connected_ssh_module.execute("aws s3 ls s3://anyvision-testing")

    @property
    def client(self):
        if self._client is None:
            self._client = self._s3_client()
        return self._client

    def _s3_client(self):
        self.config_aws()
        s3 = boto3.client('s3')  # Configure locally access keys on local machine in ~/.aws, this will use them
        return s3

    def upload_from_filesystem(self, local_path, upload_dir=""):
        if os.path.isfile(local_path):
            upload_path = os.path.join(upload_dir, os.path.basename(local_path))
            try:
                res = self.client.upload_file(local_path, "anyvision-testing", upload_path,
                                              Callback=ProgressPercentage(local_path))
            except ClientError as e:
                logging.exception(f"error uploading {e}")
        else:
            raise Exception(f"file {local_path} doesnt exist")

    def download_to_filesystem(self, remote_path, local_dir="."):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        local_file_path = os.path.join(local_dir, os.path.basename(remote_path))
        self.client.download_file("anyvision-testing", remote_path, local_file_path)

        return local_file_path

    def deploy_resource_to_s3(self, resource_path, s3_path):
        bucket = "automation_infra"
        with BytesIO() as file_obj:
            self.client.download_fileobj("anyvision-testing", resource_path, file_obj)
            file_obj.seek(0)
            self._host.Seaweed.upload_fileobj(file_obj, bucket, s3_path)
        return f'{bucket}/{s3_path}'

    def get_s3_files(self, bucket='anyvision-testing', prefix=''):
        """Get a list of files in an S3 bucket."""
        files = []
        resp = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in resp['Contents']:
            files.append(obj['Key'])
        return files

    def ping(self):
        files = self.get_s3_files()
        return True

    def verify_functionality(self):
        logging.debug("verifying resource_manager functionality")
        anv_testing_bucket = "anyvision-testing"
        files = self.get_s3_files(anv_testing_bucket, "")
        self.upload_from_filesystem("media/high_level_design.xml", "temp/")
        assert self.file_exists(anv_testing_bucket, "temp/high_level_design.xml")
        self.delete_file(anv_testing_bucket, 'temp/high_level_design.xml')
        assert not self.file_exists(anv_testing_bucket, "temp/high_level_design.xml")
        logging.debug("<<<<<<<<<RESOURCE_MANAGER PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>>>>>>")
        return True


plugins.register('ResourceManager', ResourceManager)


class ProgressPercentage(object):

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # Set this object as a callbck to upload/download file to print progress to stdout.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()
