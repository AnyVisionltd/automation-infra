from helpers import hardware_config


@hardware_config(cluster={"host1": {"ram": 10, "host_type": "virtual"}, "host2": {"gpu": (1,), "gpu_type": "1080Ti"}})
def test_host_construction(base_config):
    #print("running test_host_construction...")
    base_config.cluster.hosts.host2.test = 'host2test'
    base_config.mistake.field = 'mistakeField'
    assert base_config.cluster.hosts.host2.test == 'host2test'
    assert base_config.mistake.field == 'mistakeField'
    assert base_config.alias == 'config1'
    assert base_config.cluster.hosts.host1.Host.alias == 'monster'
    #print("passed all tests!")

