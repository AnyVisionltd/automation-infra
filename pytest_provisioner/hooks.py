from pluggy import HookspecMarker
hookspec = HookspecMarker("pytest")


def pytest_before_group_items(session, config, items):
    """
    Enables enriching test items with more properties to be used for grouping or other purposes.
    The goal is for whoever needs to be able to add item.test_group field
    """

@hookspec(firstresult=True)
def pytest_can_run_together(item1, item2):
    """
    receives 2 items and decides if they can run together.
    returns bool
    """


def pytest_after_group_items(session, config, items):
    """
    Allows doing manipulations or enriching with other data on test items (after grouping)
    Items have a test_group field.
    """


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