import pytest
from pluggy import HookspecMarker

hookspec = HookspecMarker("pytest")


def pytest_start_subprocess(item, worker):
    """
    TODO: check if the worker has hardware. if not, provision.
    Called just after submitting item to run in TheadpoolExecutor,
    before building subprocess pytest command.
    This hook is useful for running code which can take a while (so we dont want it to run on the main thread),
    but which needs to happen before building pytest command, ie provisioning a remote machine, etc.
    """


def pytest_before_running_test(item):
    """
    Called just before doing subprocess.run(command).
    If hardware is being provisioned or anything like that, it should be ready by now.
    This hook is useful to implement if some setup needs to be done before running the
    actual test, ie installing something, etc.
    """


def pytest_after_running_test(item):
    """
    Called just after doing subprocess.run(command)
    """


def pytest_end_subprocess(item, worker):
    """
    TODO: if grouper isnt invoke, need to release provisioned hardware here.
        otherwise, wait for grouper to release it when handling group has finished
    Called just after running the item in TheadpoolExecutor, after test on subprocess.run finished,
    ie item.ran = True, just before the testprotocol is called.

    """

@pytest.hookspec(firstresult=True)
def pytest_build_items_iter(session, workers):
    """
    Called before splitting off into --num-parallel threads on executor.
    Its the last chance to run something on the session as a whole.
    """

@pytest.hookspec(firstresult=True)
def pytest_get_next_item(session, worker):
    """
    """