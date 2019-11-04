class BaseConfig(object):

    def __init__(self, config_name, cluster, streaming_service):
        self.config_name = config_name
        self.cluster = cluster
        self.streaming_service = streaming_service

    def __str__(self):
        return self.config_name
