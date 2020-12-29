from pluggy import HookspecMarker
hookspec = HookspecMarker("pytest")



def pytest_before_group_items(session, config, items):
    """
    Enables enriching test items with more properties to be used for grouping or other purposes.
    The goal is for whoever needs to be able to add item.test_group field
    """

@hookspec(firstresult=True)
def pytest_can_run_together(item1, item2, firstresult=True):
    """
    receives 2 items and decides if they can run together.
    returns bool
    """


def pytest_after_group_items(session, config, items):
    """
    Allows doing manipulations or enriching with other data on test items (after grouping)
    Items have a test_group field.
    """


def pytest_before_provisioning(session, config, items):
    """
    """


def pytest_after_provisioning(session, config, items):
    """
    """


def pytest_before_subprocess_run(session):
    """
    hook is invoked immediately before calling test groups invocation on a subprocess
    """


def pytest_after_subprocess_run(session):
    """
    hook is invoked after calling test groups on a subprocess.
    At this point the reports are written to disk so it is possible to load them and manipulate if necessary.
    """

