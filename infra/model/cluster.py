from infra.model.host import Host


class Cluster(object):

    def __init__(self, alias, host_params):
        self.hosts = []
        for host_param in host_params:
            host = Host(**host_param)
            self.hosts.append(host)
        self.alias = alias

    def __str__(self):
        return self.alias
