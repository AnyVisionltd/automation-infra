import paramiko
import io


def from_string(pkey_string):
    file_obj = io.StringIO(pkey_string)
    return paramiko.RSAKey.from_private_key(file_obj)


def to_string(pkey):
    file_obj = io.StringIO()
    pkey.write_private_key(file_obj)
    file_obj.seek(0)
    content = file_obj.read()
    return content