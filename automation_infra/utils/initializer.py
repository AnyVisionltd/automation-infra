import concurrent
import logging
import os

from automation_infra.plugins.ip_table import Iptables
from automation_infra.utils import concurrently
from pytest_automation_infra import helpers


def clean(host):
    logging.debug(f"cleaning host {host.ip}, restarting automation_proxy")
    helpers.restart_proxy_container(host)
    logging.debug("resetting iptables")
    host.Iptables.reset_state()


def clean_infra_between_tests(hosts):
    concurrently.run([(clean, host) for name, host in hosts])
