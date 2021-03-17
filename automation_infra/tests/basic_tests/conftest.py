# This is a way to populate all tests in a folder with a specific installer if installer is not specified:
def pytest_fixture_setup(request):
    installer = getattr(request.module, "installer", None)
    if not installer:
        request.module.installer = "ssh"
