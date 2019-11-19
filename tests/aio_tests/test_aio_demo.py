import os
import random
import time
import pytest

from infra.model.host import Host

from infra.plugins.memsql import Memsql
from infra.plugins.pipeng import PipeNg
from infra.plugins.seaweed import Seaweed
from infra.plugins.ssh import SSH
from infra.plugins.consul import Consul
from infra.plugins.kafka import Kafka
from infra.plugins.camera_service import CameraService

from runner.helpers import hardware_config


# These are all example tests:
@hardware_config(hardware={"type": "aio"})
def test_ssh(host):
    print("Running ssh test!")
    os.system("echo this is a test > /tmp/temp.txt")
    host.SSH.put('/tmp/temp.txt', '/tmp')
    res = host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    host.SSH.execute('rm /tmp/temp.txt')
    res = host.SSH.execute('ls /tmp')
    assert 'temp.txt' not in res.split()


@hardware_config(hardware={"type": "aio"})
def test_s3(host):
    host.Seaweed.create_bucket('test_bucket')
    content = host.Seaweed.get_buckets()
    assert b'test_bucket' in content
    host.Seaweed.delete_bucket('test_bucket')
    content = host.Seaweed.get_buckets()
    assert b'test_bucket' not in content


@hardware_config(hardware={"type": "aio"})
def test_memsql_add_suspect(host):
    poi_id = random.randint(0, 999999)
    query = f'''INSERT INTO `reid_db`.`poi`
            (`poi_id`,`detection_type`,`is_ignored`,`feature_id`,`features`,`valid_until`)
            VALUES
            ({poi_id},1,0,123,123,4141);'''
    res = host.Memsql.upsert(query)
    assert res == 1


@hardware_config(hardware={"type": "aio"})
def test_pipeng_features(host):
    response = host.PipeNg.health_check()
    assert response.status == 1


@hardware_config(hardware={"type": "aio"})
def test_consul_get_services(host):
    _, services_dict = host.Consul.get_services()
    assert len(services_dict) > 0
    assert 'camera-service' in services_dict
    put_key, put_val = ("test_key", "test_val")
    res = host.Consul.put_key(put_key, put_val)
    assert res is True
    val = host.Consul.get_key("test_key")
    assert val.decode('utf-8') == put_val


@hardware_config(hardware={"type": "aio"})
def test_kafka_functionality(host):
    topics = host.Kafka.get_topics()
    assert len(topics.topics) > 0
    success = host.Kafka.create_topic('oris_new_topic')
    assert success
    time.sleep(5)
    success = host.Kafka.delete_topic('oris_new_topic')
    assert success


@hardware_config(hardware={"type": "aio"})
def test_camera_service(host):
    cameras = host.CameraService.get_cameras()
    print(cameras)
    assert 1

# @pytest.mark.parametrize("file_name, expected_faces",
#                          [
#                            ('crowd_2.jpg', 44),
#                            ('crowd_3.jpg', 26),
#                            ('sample.csv', 0),
#                            ('sample.txt', 0),
#                            ('sample.pdf', 0),
#                            ('no_face_1.jpg', 0),
#                            ('nitzan_mugshot.png', 1),
#                            ('no_face_2.jpeg', 0),
#                            ('closeup.jpg', 1),
#                            ('David.jpg', 1),
#                            ('profile_1.jpg', 1),
#                            ('profile_2.jpg', 1),
#                            ('3_faces.jpg', 3),
#                            ('high_rez_720_1020.jpg', 1),
#                            ('high_rez_1645_2339.png', 1),
#                            ('paint_1.jpeg', 0),
#                            ('paint_2.jpeg', 1),
#                            ('Wino.jpg', 1),
#                            ('brad_pitt.jpg', 1),
#                            ('brad_pitt_180.jpg', 1),
#                            ('brad_pitt_90.jpg', 1),
#                            ('brad_pitt_45.jpg', 0),
#                            ('brad_pitt_flip.jpg', 1),
#                            ('small_image_180_180.jpeg', 1),
#                            ('man_ignore.jpg', 1),
#                            ('adi_track.jpg', 1),
#                            ('adi_mugshot.jpg', 1),
#                            ('hila_track.jpg', 1),
#                            ('hila_mugshot.jpg', 1),
#                            ('6_weman_faces.jpeg', 6),
#                            ('20_faces.jpg', 18),
#                            ('10_faces.jpg', 10),
#                            ('16_different_faces.jpg', 16),
#                            ('6_kid_faces.jpg', 6),
#                            ('11_faces.jpg', 1),
#                            ('4_faces.jpg', 4),
#                            ('40_faces.png', 35),
#                            ('41_faces.jpg', 41),
#                            ('Chen.jpg', 1),
#                            ('Noy.jpg', 1),
#                            ('Raz.jpg', 1),
#                            ('Sagi.jpg', 1),
#                            ('small_face_doctor.png', 1)
#                          ]
#                          )
#@config(CLUSTER:{'host1' : , 'host2'})
def dis_test_count_crops_per_file(host, file_name, expected_faces):
    host.hosts.host1.Seaweed.get

    # This is implementation of Itays (already written) test (!)
    channel = host.cluster.hosts.host1.Host.PipeNg.get_channel()
    # TODO: I dont want to init the host even
    full_path = host.hosts.host1. Seaweed.get_full_seaweed_path(file_name)
    response = get_features(channel, full_path)
    crop_images_count = len(response.result[0].data)
    result_dic = dict()
    print(f'number of faces detected: {crop_images_count}')
    if crop_images_count > 0:
        for i in range(crop_images_count):
            result_dic[response.result[0].data[i].image] = response.result[0].data[i].features
    else:
        print(f'not features returned for {full_path}')

    # TODO: need to implement this? It "checks" if the crops were actually created...
    # is_image_created_in_seaweed(crops_dict)
    detected_faces = len(result_dic)
    assert detected_faces == expected_faces

