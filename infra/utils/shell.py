import subprocess
import logging

def run_cmd(cmd):
    args = cmd.split(' ')
    logging.debug("running command %s", args)
    return subprocess.check_output(args, shell=False).decode().strip()