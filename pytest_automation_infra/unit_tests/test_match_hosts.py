import pytest
from munch import *

import pytest_automation_infra


def test_match_hw_reqs():
    hw_reqs = {"host1": {}, "host2": {}}
    base = Munch.fromDict({"hosts": {"host1": {}}})
    with pytest.raises(Exception):
        res = pytest_automation_infra.match_base_config_hosts_with_hwreqs(hw_reqs, base)

    res = pytest_automation_infra.match_base_config_hosts_with_hwreqs({"host": {}},
                                                              Munch.fromDict({"hosts": {"host0": {}}}))
    assert set(res.hosts.keys()) == set(["host"])

    res = pytest_automation_infra.match_base_config_hosts_with_hwreqs({"host1": {}, "host2": {}},
                                                              Munch.fromDict({"hosts": {"host0": {}, "host3": {}}}))
    assert set(res.hosts.keys()) == set(["host1", "host2"])

    res = pytest_automation_infra.match_base_config_hosts_with_hwreqs({"blabla": {}, "host0": {}},
                                                              Munch.fromDict({"hosts": {"host0": {}, "host3": {}}}))
    assert set(res.hosts.keys()) == set(["blabla", "host0"])

    res = pytest_automation_infra.match_base_config_hosts_with_hwreqs({"blabla": {}, "host0": {}, "host": {}},
                                                              Munch.fromDict({"hosts": {"host0": {}, "host3": {}, "host":{}, "host2": {}}}))
    assert set(["blabla", "host0", "host"]) <= set(res.hosts.keys())
