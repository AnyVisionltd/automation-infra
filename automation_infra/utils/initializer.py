import logging

from automation_infra.plugins import tunnel_manager
from automation_infra.plugins import ip_table
from automation_infra.plugins import admin
from automation_infra.utils import concurrently
from pytest_automation_infra import helpers


def clean(host, item, clean_between_tests_hook):
    logging.debug(f"cleaning host {host.ip}")
    host.SshDirect.disconnect()
    host.clear_plugins()
    logging.debug("resetting iptables")
    host.Iptables.reset_state()
    # Flushing journal to only have journal of current test if needed
    host.Admin.flush_journal()
    clean_between_tests_hook(host=host, item=item)
    host.Admin.log_to_journal(f">>>>> Test {item.nodeid} <<<<")


def clean_infra_between_tests(hosts, item, hook):
    concurrently.run([(clean, host, item, hook) for _, host in hosts])
