import random

import pytest

from infra.model.host import Host

from infra.modules.memsql import Memsql
from infra.modules.pipeng import PipeNg
from infra.modules.seaweed import Seaweed
from infra.modules.ssh import SSH


# These are all example tests:
def test_host_construction(base_config):
    base_config.cluster.hosts.host2.test = 'host2test'
    base_config.mistake.field = 'mistakeField'
    assert base_config.cluster.hosts.host2.test == 'host2test'
    assert base_config.mistake.field == 'mistakeField'
    assert base_config.alias == 'config1'
    assert base_config.cluster.hosts.host1.Host.alias == 'monster'


def test_ssh(base_config):
    assert base_config.cluster.hosts.host1.ip == '192.168.20.34'
    contents = base_config.cluster.hosts.host1.Host.SSH.get_contents('/tmp/f1.txt')
    assert contents == b's is a tew\nawetoawefjaw\nafwefoj\n'


def test_s3(base_config):
    img_path = 'Screenshot%20from%202019-09-16%2017-44-29.png'
    res = base_config.cluster.hosts.host1.Host.Seaweed.get_image(img_path)
    assert res.status_code == 200


def test_add_suspect(base_config):
    poi_id = random.randint(0, 999999)
    query = f'''INSERT INTO `reid_db`.`poi`
            (`poi_id`,`detection_type`,`is_ignored`,`feature_id`,`features`,`valid_until`)
            VALUES
            ({poi_id},1,0,123,123,4141);'''
    res = base_config.cluster.hosts.host1.Host.Memsql.upsert(query)
    assert res == 1


def test_get_features(base_config):
    image_path = r'file:///tmp/accuracy_test/ori.jpg'
    response = base_config.cluster.hosts.host1.Host.PipeNg.get_features(image_path)
    assert response.result[0].data[0].detector_score == 0.9088160991668701




