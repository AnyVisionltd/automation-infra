import queue
import random


class Group:
    def __init__(self, id=None, items=None):
        self.id = id if id is not None else random.randint(0, 100)
        if items:
            self.items = items
            for test in self.items:
                test.test_group = self
        else:
            self.items = list()
        self.kill_hb = None
        self.provisioned_hardware = None
        self.subprocess_run_future = None
        self.items_queue = queue.Queue()

    @property
    def hardware_reqs(self):
        return self.items[0].__hardware_reqs if self.items else None

    def attach(self, item):
        item.test_group = self
        self.items.append(item)

    @staticmethod
    def assign_to_new_group(item, groups):
        group = Group(id=len(groups))
        group.attach(item)
        groups.append(group)
