import base64
import logging
import os
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
import sys
import threading

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from infra.model import plugins

logging.getLogger('botocore').setLevel(logging.WARN)


class ResourceManager(object):
    def __init__(self, host):
        self._host = host
        self._client = None
        self._resource = None

    def config_aws(self):
        if not os.path.exists(f'{os.path.expanduser("~")}/.aws'):
            raise FileNotFoundError("Missing aws credentials in ~/.aws folder")

    @property
    def client(self):
        if self._client is None:
            self._client = self._s3_client()
        return self._client

    def _s3_client(self):
        self.config_aws()
        s3 = boto3.client('s3')  # Configure locally access keys on local machine in ~/.aws, this will use them
        return s3

    @property
    def resource(self):
        if self._resource is None:
            self._resource = self._s3_resource()
        return self._resource

    def _s3_resource(self):
        self.config_aws()
        return boto3.resource('s3')

    def upload_from_filesystem(self, local_path, upload_dir=""):
        upload_path = None
        if os.path.isfile(local_path):
            upload_path = os.path.join(upload_dir, os.path.basename(local_path))
            try:
                res = self.client.upload_file(local_path, "anyvision-testing", upload_path,
                                              Callback=ProgressPercentage(local_path))
            except ClientError as e:
                logging.exception(f"error uploading {e}")
                raise Exception(f"error uploading {e}")
        else:
            raise Exception(f"file {local_path} doesnt exist")
        return upload_path

    def download_to_filesystem(self, remote_path, local_dir="."):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        local_file_path = os.path.join(local_dir, os.path.basename(remote_path))
        self.client.download_file("anyvision-testing", remote_path, local_file_path)

        return local_file_path


    def deloy_resource_to_proxy_container(self, resource_path, remote_path):
        with BytesIO() as file_obj:
            self.client.download_fileobj("anyvision-testing", resource_path, file_obj)
            file_obj.seek(0)
            self._host.SSH.put_content_from_fileobj(file_obj, remote_path)

    def deploy_multiple_resources_to_proxy_container(self, aws_file_list, remote_dir):
        resources_s3_list = []

        for resource in aws_file_list:
            resource_name = os.path.basename(resource)
            remote_path = os.path.join(remote_dir, resource_name)
            self.deloy_resource_to_proxy_container(resource, remote_path)

        return resources_s3_list

    def get_raw_resource(self, resource_path, bucket="anyvision-testing", as_base64=False):
        with BytesIO() as file_obj:
            self.client.download_fileobj(bucket, resource_path, file_obj)
            file_obj.seek(0)
            file_bytes = file_obj.read()
            return base64.b64encode(file_bytes).decode("utf-8") if as_base64 else file_bytes

    def get_s3_files(self, bucket='anyvision-testing', prefix=''):
        """Get a list of files in an S3 bucket."""
        files = []
        resp = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in resp['Contents']:
            files.append(obj['Key'])
        return files

    def ping(self):
        try:
            files = self.get_s3_files()
            return True
        except Exception:
            raise ConnectionError

    def get_bucket_files(self, bucket_name, recursive=True):
        return self.get_files_by_prefix(bucket_name, '', recursive)

    def get_all_buckets(self):
        return list(self.resource.buckets.all())

    def get_files_by_prefix(self, bucket_name, prefix, recursive=True):
        res = self.client.list_objects(Bucket=bucket_name, Prefix=prefix)
        res_code = res['ResponseMetadata']['HTTPStatusCode']
        assert res_code == 200
        files = [x['Key'] for x in res.get('Contents', [])]
        if not recursive:
            return files
        for x in res.get('CommonPrefixes', []):
            prefix = x['Prefix']
            files.extend(self.get_files_by_prefix(bucket_name, prefix))
        return files

    def create_bucket(self, bucket_name):
        res = self.client.create_bucket(Bucket=bucket_name)
        res_code = res['ResponseMetadata']['HTTPStatusCode']
        assert res_code == 200

    def delete_bucket(self, bucket_name):
        res = self.client.delete_bucket(Bucket=bucket_name)
        res_code = res['ResponseMetadata']['HTTPStatusCode']
        assert res_code == 204

    def upload_file_to_bucket(self, src_file_path, dst_bucket, ds_file_name):
        res = self.client.upload_file(src_file_path, dst_bucket, ds_file_name)
        assert res is None

    def upload_fileobj(self, file_obj, dst_bucket, dst_filepath):
        res = self.client.upload_fileobj(file_obj, dst_bucket, dst_filepath)
        assert res is None

    def upload_files_from(self, path, dst_bucket):
        self.create_bucket(dst_bucket)
        src_files = os.listdir(path)
        dst_files = self.get_bucket_files(dst_bucket)
        missing_files = [item for item in src_files if item not in dst_files]
        for _file in missing_files:
            self.upload_file_to_bucket(path + _file, dst_bucket, _file)

    def file_exists(self, bucket_name, file_name):
        try:
            self.client.head_object(Bucket=bucket_name, Key=file_name)
        except ClientError:
            return False
        else:
            return True

    def file_content(self, bucket_name, key):
        res = self.client.get_object(Bucket=bucket_name, Key=key)
        assert res['ResponseMetadata']['HTTPStatusCode'] == 200
        return res['Body'].read()

    def check_video_path(self, bucket_name, key):
        res = self.client.get_object(Bucket=bucket_name, Key=key)
        assert res['ResponseMetadata']['HTTPStatusCode'] == 200
        return res

    def get_files_in_dir(self, bucket_name, dir_path):
        result = []
        resp = self.client.list_objects_v2(Bucket=bucket_name, Prefix=dir_path, Delimiter='/')
        if 'Contents' not in resp.keys():
            return
        return [obj['Key'] for obj in resp['Contents']]

    def delete_file(self, bucket_name, file_name):
        self.client.delete_object(Bucket=bucket_name, Key=file_name)
        assert not self.file_exists(bucket_name, file_name)

    def verify_functionality(self):
        logging.info("verifying resource_manager functionality")
        anv_testing_bucket = "anyvision-testing"
        files = self.get_s3_files(anv_testing_bucket, "")
        self.upload_from_filesystem("media/high_level_design.xml", "temp/")
        assert self.file_exists(anv_testing_bucket, "temp/high_level_design.xml")
        self.delete_file(anv_testing_bucket, 'temp/high_level_design.xml')
        assert not self.file_exists(anv_testing_bucket, "temp/high_level_design.xml")
        resource_to_test = files[0]
        test_content = self.get_raw_resource(resource_to_test)
        self.deloy_resource_to_proxy_container(resource_to_test, "/tmp/resource")
        fs_content = self._host.SSH.get_contents("/tmp/resource")
        assert fs_content == test_content
        self.deploy_multiple_resources_to_proxy_container(files[0:2], "/tmp/resource_multiple")
        filesnum = int(self._host.SSH.execute("ls -1 /tmp/resource_multiple | wc -l").strip())
        assert filesnum == 2
        logging.info("<<<<<<<<<RESOURCE_MANAGER PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>>>>>>")
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
