import logging
import os
import time
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
import sys
import threading

from automation_infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins


class ResourceManager(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.client = boto3.client('s3', aws_access_key_id='AKIAZQJT5HXO4YTJSHHL',
                                   aws_secret_access_key='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' #,
                                   # TODO for tunnel?: endpoint_url=f'localhost:{self.local_bind_port}'
                                    )

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
        self.client.download_file("anyvision-testing", remote_path,
                                  os.path.join(local_dir, os.path.basename(remote_path)))

    def deploy_resource_to_s3(self, resource_path, s3_path):
        with BytesIO() as file_obj:
            self.client.download_fileobj("anyvision-testing", resource_path, file_obj)
            file_obj.seek(0)
            self._host.Seaweed.upload_fileobj(file_obj, "automation_infra", s3_path)
            return f"s3:///automation_infra/{s3_path}"


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
