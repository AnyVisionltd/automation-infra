def get_first_item_list(received_list):
    return received_list[0]


def get_pyobject(length):
    return list(range(length))


def use_external_lib(uri):
    import requests
    return requests.get(uri).status_code


class Person(object):

    def __init__(self, name):
        self.name = name


def send_class(person, name):
    assert isinstance(person, Person), "not a person"
    person.name = name
    return person


def catch_exception(exec_type):
    raise exec_type


def background_task():
    import time
    time.sleep(3)
    return True
