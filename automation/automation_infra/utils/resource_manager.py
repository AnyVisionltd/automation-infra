import logging
import os

import boto3
from botocore.exceptions import ClientError
import sys
import threading


client = boto3.client('s3', aws_access_key_id='AKIAZQJT5HXO4YTJSHHL', aws_secret_access_key='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')


def upload(file_path, upload_dir=""):
    """This uploads only files. Directory wont work.
    args:
        file_path is path to a FILE,
        upload_dir is the DIRECTORY to put the file in, not including filename.
    """
    if os.path.isfile(file_path):
        upload_path = os.path.join(upload_dir, os.path.basename(file_path))
        try:
            client.upload_file(file_path, "anyvision-testing", upload_path,
                                          Callback=ProgressPercentage(file_path))
        except ClientError as e:
            logging.error(f"error uploading {e}")
    else:
        raise Exception(f"file {file_path} doesnt exist")


def download(remote_path, local_dir="."):
    """This can download a file only, folders wont download with this.
        Args:
            remote_path is path to a FILE on S3 in anyvision-testing bucket,
            local_dir the DIRECTORY you would like to download file to, not including filename
    """
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    client.download_file("anyvision-testing", remote_path, os.path.join(local_dir, os.path.basename(remote_path)))


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()
