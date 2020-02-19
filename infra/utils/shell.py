import subprocess
import logging

def run_cmd(cmd, shell=False):
    logging.debug("running command %s", cmd)
    return subprocess.check_output(cmd, shell=shell).decode().strip()