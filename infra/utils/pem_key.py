import paramiko
import io


def from_string(pkey_string):
    file_obj = io.StringIO(pkey_string)
    return paramiko.RSAKey.from_private_key(file_obj)

