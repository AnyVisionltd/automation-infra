import logging
import pytest

import pytest_provisioner


@pytest.hookimpl(trylast=True)
def pytest_can_run_together(item1, item2):
    """
    This is the trivial implementation if no one else implemented this hook.
    It does a trivial comparison of hardware_reqs adn cluster_config.
    """
    if item1.function.__hardware_reqs == item2.function.__hardware_reqs and \
            item2.function.__cluster_config == item2.function.__cluster_config:
        return True
    return False


def pytest_finished_handling_group(session, worker):
    logging.info("finished handling group, releasing group hardware..")
    pytest_provisioner.release_worker_hardware(session, worker)


