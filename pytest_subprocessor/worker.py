import json
import logging
import os
import re
import subprocess
import sys
import uuid
from concurrent.futures.thread import ThreadPoolExecutor


def sanitize_nodeid(filename):
    filename = filename.replace('::()::', '/')
    filename = filename.replace('::', '/')
    filename = filename.replace('<', '')
    filename = filename.replace('>', '')
    filename = re.sub(r'\[(.+)\]', r'-\1', filename)
    return filename


class Worker:
    def __init__(self, session):
        self.id = str(uuid.uuid4())
        self.session = session
        self.fut = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=self.id,)
        self.handled_items = list()

    def start(self):
        fut = self.executor.submit(self.run_tests)
        fut.worker = self
        self.fut = fut
        
    def refresh_id(self):
        self.id = str(uuid.uuid4())

    @property
    def completion(self):
        return self.fut

    def run_tests(self):
        item = self.session.config.hook.pytest_get_next_item(session=self.session, worker=self)
        while item:
            self.run_on_subprocess(item)
            item = self.session.config.hook.pytest_get_next_item(session=self.session, worker=self)

    def run_on_subprocess(self, item):
        item.id = str(uuid.uuid4())
        # Time to provision if you want..
        item.config.hook.pytest_start_subprocess(item=item, worker=self)
        command = self.build_pytest_prefix(item)
        test_full_path = self.build_fullpath(item)
        command.append(test_full_path)
        keyword_expression = self.build_keyword_expression(item)
        command.append(keyword_expression)
        logging.debug(f"command: {command}")
        # Set up something (not install yet bc for install you need base_config)
        item.config.hook.pytest_before_running_test(item=item)
        logging.debug(f"\n\nrunning test {os.path.basename(item.nodeid)} on subprocess")
        timeout_sec = item.config.getoption("timeout", None)
        self.run_subprocess_tests(command, timeout_sec)
        self.handled_items.append(item)
        item.config.hook.pytest_after_running_test(item=item)
        item.config.hook.pytest_end_subprocess(item=item, worker=self)

    def build_pytest_prefix(self, item):
        # this makes sure there aren't secondary_flags with spaces (which fucks up subprocess.run command):
        secondary_flags = self.split_intelligently(item.config.option.secondary_flags)
        count = f'--count {item.config.getoption("--count", None)}' if item.config.getoption("--count", None) else ''
        pytest_prefix = f"{sys.executable} -m pytest -p pytest_subprocessor.serializer -p no:logging --session-id {self.id} --item-id {item.id} {count} -s"
        pytest_prefix = pytest_prefix.split()
        logs_dir = os.path.join(item.config.option.logger_logsdir, "test_logs", sanitize_nodeid(os.path.split(item.nodeid)[1]))
        os.makedirs(logs_dir, exist_ok=True)
        pytest_prefix.extend(["--logs-dir", logs_dir])
        pytest_prefix.extend(secondary_flags)
        return pytest_prefix

    @staticmethod
    def split_intelligently(flags):
        """Splits flags which have spaces in them, unless they are json strings in which case leaves them alone
        This is necessary because flags could in theory be json.dumped strings"""
        result = []
        for flag in flags:
            try:
                json.loads(flag)
                result.append(flag)
            except json.JSONDecodeError:
                result.extend(flag.split())
        return result

    @staticmethod
    def build_fullpath(item):
        return os.path.join(item.config.rootdir, f'{item.nodeid.split("[")[0]}')

    @staticmethod
    def build_keyword_expression(item):
        """Its hard to explain why this is necessary, but parametrized tests have [1-5] appended to their nodeid.
        In order to only run test once, its necessary to add -k and only the specific nodeid we would like.
        pytest -k arg does 'only run tests which match the given substring expression.' (see pytest help)"""
        parametrized = item.nodeid.split('[')[1] if len(item.nodeid.split('[')) > 1 else ''
        return f"-k {parametrized}"

    @staticmethod
    def run_subprocess_tests(command, timeout=None):
        try:
            subprocess.run(command, timeout=timeout)
            # TODO: check if as soon as I got an error here the process was kill? if not, try at first with sigint,
            #  and then afterwards if this didnt work with sigkill
        except TimeoutError:
            logging.error("test timed out.")
            # TODO:  call pytest_after_test on subprocess
            # TODO: call test teardown logic on subprocess - the logic itself will be implemented by someone else (test writer)
            # We can either
                # save the test command which timed out -
                    # better because then we will have the item and can hopefully call runtest_teardown somehow
                # decide by the serialized reports which were written to the disk.
        except:
            raise
