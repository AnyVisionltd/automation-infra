import pytest

from pytest_automation_infra.helpers import hardware_config
from .snippet_test_functions import get_pyobject, use_external_lib, send_class, catch_exception, background_task
from .snippet_test_functions import Person


@hardware_config(hardware={'host': {}})
@pytest.mark.parametrize('target, args, kwargs, expected, run_background', (
        (get_pyobject, (5,), {}, lambda x: x == get_pyobject(5), False),
        (use_external_lib, (), {'uri': 'http://google.com'}, lambda x: x == use_external_lib('http://google.com'), False),
        (send_class, (), {'person': Person('david'), 'name': 'moshe'}, lambda x: x.name == 'moshe', False),
        (catch_exception, (RuntimeError,), {}, lambda x: type(x) is RuntimeError, False),
        (background_task, (), {}, lambda x: x is True, True)
))
def test_snippet(base_config, target, args, kwargs, expected, run_background):
    ssh = base_config.hosts.host.SSH
    try:
        if run_background:
            background = ssh.run_background_snippet(target, *args, **kwargs)
            result = background.wait_result()
        else:
            result = ssh.run_snippet(target, *args, **kwargs)

    except Exception as e:
        assert expected(e), str(e)

    else:
        assert expected(result), str(result)
