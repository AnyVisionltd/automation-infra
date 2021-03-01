import logging
from munch import *

from infra.model.host import Host
from pytest_automation_infra import init_cluster_structure


def test_init_clusters():
    base_config = DefaultFactoryMunch(Munch)
    base_config.hosts.host1 = Host.from_args('1.2.3.1', 'u', 'p', alias='h1')
    base_config.hosts.host2 = Host.from_args('1.2.3.2', 'u', 'p', alias='h2')
    base_config.hosts.host3 = Host.from_args('1.2.3.3', 'u', 'p', alias='h3')
    base_config.hosts.host4 = Host.from_args('1.2.3.4', 'u', 'p', alias='h4')

    # To check that this doesnt break any existing tests...
    init_cluster_structure(base_config, None)

    grouping = {
        "cluster1": {"hosts": ["host1", "host2", "host3"]},
        "cluster2": {"hosts": ["host4"], "random_key1": ["val1", "val2"], "random_key2": 2}}
    init_cluster_structure(base_config, grouping)

    assert base_config.clusters.cluster1.hosts.host1 is base_config.hosts.host1
    assert base_config.clusters.cluster1.hosts.host2 is base_config.hosts.host2
    assert base_config.clusters.cluster2.hosts.host4 is base_config.hosts.host4

