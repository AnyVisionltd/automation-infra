import logging
import os
import queue
from collections import defaultdict

import pytest

from pytest_grouper.groups import Group


def pytest_addhooks(pluginmanager):
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


def pytest_sessionstart(session):
    session.worker_map = defaultdict(dict)  # {worker_id: {"items_queue": iterator, } }


def pytest_collection_modifyitems(session, config, items):
    config.hook.pytest_before_group_items(session=session, config=config, items=items)
    group_items(session, items, config.hook)
    config.hook.pytest_after_group_items(session=session, config=config, items=items)

    # TODO: set test.teardown() property?


def group_items(session, items, hook):
    if not items:
        logging.info("didnt find any items")
        os._exit(666)
    session.groups = list()
    Group.assign_to_new_group(items[0], session.groups)
    for idx in range(1, len(items)):
        for group in session.groups:
            together = hook.pytest_can_run_together(item1=group.items[0], item2=items[idx])
            if together:
                group.attach(items[idx])
                break
        if not getattr(items[idx], "test_group", None):
            Group.assign_to_new_group(items[idx], session.groups)
    logging.info(f"groups: {[len(group.items) for group in session.groups]}\n"
                 f"{[group.items for group in session.groups]}")


@pytest.hookimpl(tryfirst=True)
def pytest_build_items_iter(session, workers):
    session.groups_iter = iter(session.groups)
    for group in session.groups:
        group.items_queue.queue = queue.deque(group.items)
    return True


@pytest.hookimpl(tryfirst=True)
def pytest_get_next_item(session, worker):
    if worker.id in session.worker_map:
        try:
            next_item = session.worker_map[worker.id]["items_queue"].get(block=False)
            logging.debug(f"worker {worker.id} got item {os.path.split(next_item.nodeid)[1]}")
            return next_item
        except queue.Empty:
            logging.debug(f"worker {worker.id} finished all items in group")
            session.config.hook.pytest_finished_handling_group(session=session, worker=worker)
            del session.worker_map[worker.id]
    try:
        next_group = next(session.groups_iter)
        session.config.hook.pytest_started_handling_group(session=session, worker=worker)
        session.worker_map[worker.id]['items_queue'] = next_group.items_queue
        logging.debug(f"worker {worker.id} handling new group")
        return pytest_get_next_item(session, worker)
    except StopIteration:
        logging.debug("all groups are in progress, checking for long queue..")
        longest_q = queue.Queue()
        for worker_id, worker_dict in session.worker_map.items():
            if worker_dict['items_queue'].qsize() > 1 and worker_dict['items_queue'].qsize() > longest_q.qsize():
                longest_q = worker_dict['items_queue']
        if longest_q.qsize():
            logging.debug("found long queue.. handling it")
            session.config.hook.pytest_started_handling_group(session=session, worker=worker)
            session.worker_map[worker.id]['items_queue'] = longest_q
            return pytest_get_next_item(session, worker)
        else:
            logging.debug("all groups have been exhausted")
