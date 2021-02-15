from pluggy import HookspecMarker

hookspec = HookspecMarker("pytest")


def pytest_after_base_config(base_config, request):
    """
    called after base_config has been initted successfully (and ssh has connected)
    """


def pytest_clean_between_tests(host, item):
    """
    called after infra does clean between tests. Can implement whatever you want here to reset state.
    """


def pytest_download_logs(host, dest_dir):
    """called after running test to """


def pytest_after_test(item, base_config):
    """"called after test has finished running and teardown"""
