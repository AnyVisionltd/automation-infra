from pluggy import HookspecMarker
hookspec = HookspecMarker("pytest")


def pytest_before_provisioning(item):
    """
    called right before provisioning hardware for item (and whatever group its in).
    """


def pytest_after_provisioning(item):
    """
    called right after successfully provisioning hardware for item (and group)
    """


def pytest_before_release():
    """"""


def pytest_after_release():
    """"""