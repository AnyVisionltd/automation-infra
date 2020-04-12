import logging

from automation_infra.plugins.resource_manager import ResourceManager


def init_plugins(host):
    """This method inits automation-infra plugins (if necessary) so that when
    host.clean_between_tests is called the plugins exist for the host.
    New plugins implemented in this repo should be added to this list."""
    host.ResourceManager
