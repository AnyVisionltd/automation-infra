import time
from pprint import pprint

import sshtunnel
from munch import Munch
import random

from runner import CONSTS
from infra.model import plugins

from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic, KafkaException

automation_tests_topic = 'anv.automation.topic1'
consumer_group = {"group.id": 'automation_group'}


class Kafka(object):
    def __init__(self, host=Munch(ip='0.0.0.0', user='user', password='user1!')):
        self._tunnel = sshtunnel.open_tunnel((host.ip, CONSTS.TUNNEL_PORT),
                                             ssh_username=host.user, ssh_password=host.password,
                                             ssh_pkey=host.keyfile,
                                             remote_bind_address=(CONSTS.KAFKA, CONSTS.KAFKA_PORT))
        self._tunnel.start()
        self.bs_servers = {'bootstrap.servers': f'localhost:{self._tunnel.local_bind_port}'}

        self.kafka_admin = AdminClient(self.bs_servers)
        self._c = Consumer({**self.bs_servers, **consumer_group})
        self._p = Producer(self.bs_servers)

    @property
    def consumer(self):
        """ Property, return the Kafka consumer object of this class."""
        return self._c

    @property
    def producer(self):
        return self._p

    def get_topics(self):
        topics = self.kafka_admin.list_topics(timeout=5)
        return topics

    def create_topic(self, name):
        """create topic if not exists"""
        new_topic = NewTopic(name, num_partitions=3, replication_factor=1)
        fs = self.kafka_admin.create_topics([new_topic])
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} created".format(topic))
                return True
            except KafkaException:
                # TODO: validate this exception is thrown only when topic exists and not in other cases
                # Othewise can add check before trying to create it...
                print("topic already exists")
                return True
            except Exception as e:
                print("Failed to create topic {}: {}".format(topic, e))
                raise

    def get_message(self, topic, tries=3):
        self.consumer.subscribe(topic)
        for i in range(tries):
            msg = self.consumer.poll()
            if msg is not None:
                key, value = self.parse_message(msg)
                return key, value
        return None, None

    def consume_iter(self, *topics, timeout=None, commit=False):
        """ Generator - use Kafka consumer for receiving messages from the given *topics* list.
            Yield a tuple of each message key and value.
            If got a *timeout* argument - break the loop if passed the value in seconds, but did not
            received messages since the last one was processed.
            If the optional argument *commit* is true, commit each message consumed."""
        if len(topics) == 0:
            raise TypeError('at least one topic must be received to consume_iter instance')

        print(f'Started receiving messages (timeout: {timeout}).')

        try:
            self.consumer.subscribe(list(topics))
            self._is_consuming = True
            last_ts = time.time()
            while timeout is None or time.time() - last_ts < timeout:
                msg = self.consumer.poll(timeout=0.1)
                self._last_message = msg
                if msg is None:
                    yield None, None
                elif not msg.error():
                    key, value = self.parse_message(msg)
                    print(f'Received message: {key}.')
                    yield key, value
                elif 'No more messages' not in msg.error().str():
                    error = msg.error().str()
                    raise Exception(f'an error occurred during receiving messages: {error}')

                if commit is True and msg is not None:
                    offset = msg.offset()
                    if offset < 0:
                        offset = 0
                    tpo = TopicPartition(topic=msg.topic(), partition=msg.partition(), offset=offset)
                    self.consumer.commit(offsets=[tpo], asynchronous=True)
                last_ts = time.time()
        except:
            print("Error in consume_iter")
        finally:
            joined_topics = ', '.join(topics)
            print(f"Finished receiving messages from topic/s "
                          f"'{joined_topics}'.")
            self._is_consuming = False
            self._last_message = None

    def parse_message(self, msg):
        key, value = msg.key().decode(), msg.value().decode()
        return key, value

    @staticmethod
    def delivery_report(err, msg):
        if err:
            raise
        else:
            print(f"message {msg} put successfully")

    def put_message(self, key, msg):
        self.producer.produce(topic=automation_tests_topic, key=key, value=msg, callback=self.delivery_report)
        self.producer.poll(0)

    def delete_topic(self, topic):
        fs = self.kafka_admin.delete_topics([topic], operation_timeout=30)

        # Wait for operation to finish.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} deleted".format(topic))
                return True
            except Exception as e:
                print("Failed to delete topic {}: {}".format(topic, e))


plugins.register('Kafka', Kafka)


def check_flow_works():
    kafka_obj = Kafka()
    while True:
        for key, val in kafka_obj.consume_iter(automation_tests_topic, commit=True, timeout=5):
            try:
                if key is None:
                    kafka_obj.put_message(f'key{random.randint(0,10)}', f"test {random.randint(10, 100)}")
                    continue  # When kafka reach the timeout he returns None (no new tracks)
                print(key, val)
            except Exception as e:
                print(f"caught exception: {e}")


if __name__ == '__main__':
    host = Munch(ip='0.0.0.0', user='user', password='pass', keyfile='')
    kafka_obj = Kafka(host)
    topics = kafka_obj.get_topics()
    pprint(topics.topics)
    assert len(topics.topics) > 1
    success = kafka_obj.create_topic('oris_new_topic')
    assert success
    success = kafka_obj.delete_topic('oris_new_topic')
    assert success
    kafka_obj.create_topic(automation_tests_topic)
    check_flow_works()

