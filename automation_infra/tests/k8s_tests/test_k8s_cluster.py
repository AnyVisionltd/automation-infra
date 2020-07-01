import logging
import os
import subprocess

from ruamel.yaml import YAML
import requests
from munch import DefaultFactoryMunch, Munch

from automation_infra.utils import waiter
from infra.model.host import Host
from pytest_automation_infra.helpers import hardware_config

YAML_FOLDER = f"{os.path.dirname(__file__)}/yaml_files"
CLUSTER_TEMPLATE = f"{YAML_FOLDER}/template.cluster.yml"


def create_cluster_yaml(template_file, base_config):
    yaml = YAML()
    yaml.default_flow_style = False
    with open(template_file, 'r') as config_file_template:
        config = yaml.load(config_file_template)
        node_template = config['nodes'][0]
        config['nodes'] = [node_template.copy() for host in base_config.hosts.keys()]
        for idx, host in enumerate(base_config.hosts.values()):
            config['nodes'][idx]['address'] = host.ip
    templated_cluster_file = os.path.join(os.path.dirname(template_file), "cluster.yml")
    with open(templated_cluster_file, "w") as config_file:
        yaml.dump(config, config_file)
    return templated_cluster_file

@hardware_config(hardware={"host1": {}, "host2": {}, "host3": {}},
                 grouping={"cluster1": {"hosts": ["host1", "host2", "host3"]}})
def test_k8s_cluster(base_config):
    # TODO: add support for multiple clusters?

    create_cluster_yaml(CLUSTER_TEMPLATE, base_config)

    res = subprocess.run(f"{YAML_FOLDER}/deploy_cluster.sh", shell=True)
    logging.info("finished deploying cluster")
    res = waiter.wait_nothrow(lambda: requests.get(f"http://{base_config.clusters.cluster1.hosts.host1.ip}:31000"))
    for i in range(10):
        res = requests.get(f"http://{base_config.clusters.cluster1.hosts.host1.ip}:31000")
        assert res.status_code == 200
        logging.info(f"response: {res.text}")


def unittest_create_cluster_fn():
    base_config = DefaultFactoryMunch(Munch)
    base_config.hosts.host1 = Host.from_args('h1', '1.2.3.1', 'u', 'p')
    base_config.hosts.host2 = Host.from_args('h2', '1.2.3.2', 'u', 'p')
    base_config.hosts.host3 = Host.from_args('h3', '1.2.3.3', 'u', 'p')
    created_node_ips = ['1.2.3.1', '1.2.3.2', '1.2.3.3']
    templated_file = create_cluster_yaml(CLUSTER_TEMPLATE, base_config)
    yaml = YAML()
    yaml.default_flow_style = False
    with open(templated_file, 'r') as f:
        config = yaml.load(f)
        assert len(config['nodes']) == 3
        assert set([node['address'] for node in config['nodes']]) == set(created_node_ips)
