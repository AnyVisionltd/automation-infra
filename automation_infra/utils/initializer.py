import concurrent
import logging
import os

from automation_infra.plugins import tunnel_manager
from automation_infra.plugins import ip_table
from automation_infra.utils import concurrently
from pytest_automation_infra import helpers


def clean(host):
    host.TunnelManager.clear()
    logging.debug(f"cleaning host {host.ip}, restarting automation_proxy")
    helpers.restart_proxy_container(host)
    host.clear_plugins()
    logging.debug("resetting iptables")
    host.Iptables.reset_state()


def clean_infra_between_tests(hosts):
    concurrently.run([(clean, host) for name, host in hosts])
