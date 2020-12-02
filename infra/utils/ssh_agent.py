import os
import re
import subprocess


def setup_agent():
    process = subprocess.run(['ssh-agent', '-s'], stdout=subprocess.PIPE, universal_newlines=True)
    OUTPUT_PATTERN = re.compile('SSH_AUTH_SOCK=(?P<socket>[^;]+).*SSH_AGENT_PID=(?P<pid>\d+)', re.MULTILINE | re.DOTALL)
    match = OUTPUT_PATTERN.search(process.stdout)
    if match is None:
        raise Exception('Could not parse ssh-agent output. It was: {}'.format(process.stdout))
    agentData = match.groupdict()
    os.environ['SSH_AUTH_SOCK'] = agentData['socket']
    os.environ['SSH_AGENT_PID'] = agentData['pid']
