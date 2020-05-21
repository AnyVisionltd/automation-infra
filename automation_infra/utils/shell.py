import subprocess
import logging

def run_cmd(cmd, shell=False):
    logging.debug("running command %s", cmd)
    if not shell and isinstance(cmd,str):
        cmd = cmd.split()
    return subprocess.check_output(cmd, shell=shell).decode().strip()