import logging

from automation_infra.plugins import tunnel_manager
from automation_infra.plugins import ip_table
from automation_infra.plugins import admin
from automation_infra.utils import concurrently
from pytest_automation_infra import helpers


def clean(host, test_name):
    host.TunnelManager.clear()
    logging.debug(f"cleaning host {host.ip}, restarting automation_proxy")
    host.SshDirect.disconnect()
    host.clear_plugins()
    logging.debug("resetting iptables")
    helpers.restart_proxy_container(host)
    host.Iptables.reset_state()
    # Flushing journal to only have journal of current test if needed
    host.Admin.flush_journal()
    host.Admin.log_to_journal(f">>>>> Test {test_name} <<<<")


def clean_infra_between_tests(hosts, test_name):
    concurrently.run([(clean, host, test_name) for _, host in hosts])
