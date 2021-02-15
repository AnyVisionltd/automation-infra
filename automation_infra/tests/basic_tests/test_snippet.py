import pytest

from pytest_automation_infra.helpers import hardware_config
from .snippet_test_functions import get_pyobject, use_external_lib, send_class, catch_exception, background_task, get_first_item_list
from .snippet_test_functions import Person


def _run_snippet(expected, host, run_background, target, *args, **kwargs):
    ssh = host.SshDirect
    result = None
    try:
        if run_background:
            background = ssh.run_background_snippet(target, *args, **kwargs)
            result = background.wait_result()
        else:
            result = ssh.run_snippet(target, *args, **kwargs)
    except Exception as e:
        assert expected(e), str(e)
    return result


def check_snippet_result(result, expected):
    assert expected(result), str(result)


@hardware_config(hardware={'host': {}})
@pytest.mark.parametrize('target, args, kwargs, expected, run_background', (
        (get_pyobject, (5,), {}, lambda x: x == get_pyobject(5), False),
        (use_external_lib, (), {'uri': 'http://google.com'}, lambda x: x == use_external_lib('http://google.com'), False),
        (send_class, (), {'person': Person('david'), 'name': 'moshe'}, lambda x: x.name == 'moshe', False),
        (catch_exception, (RuntimeError,), {}, lambda x: type(x) is RuntimeError, False),
        (background_task, (), {}, lambda x: x is True, True)
))
def test_snippet(base_config, target, args, kwargs, expected, run_background):
    host = base_config.hosts.host

    result = _run_snippet(expected, host, run_background, target, *args, **kwargs)
    if result:
        check_snippet_result(result, expected)


@hardware_config(hardware={'host': {}})
def test_snippet_with_big_params(base_config):
    host = base_config.hosts.host
    run_in_background = False
    target = get_first_item_list
    args = (['123' * 100 for _ in range(100000)],)
    kwargs = {}
    expected = lambda x: x == target(*args)

    result = _run_snippet(expected, host, run_in_background, target, *args, **kwargs)
    check_snippet_result(result, expected)
