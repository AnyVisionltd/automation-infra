import sys
import pytest


class TestCollector:

    def __init__(self):
        self.collected = []

    def pytest_collection_modifyitems(self, items):
        for item in items:
            self.collected.append(item)


if __name__ == '__main__':
    collector = TestCollector()
    directory = './tests/aio_tests/test_aio_demo.py'
    pytest.main(['--collect-only', directory], plugins=[collector])

    for node in collector.collected:
        print(node.obj.__hardware_reqs)