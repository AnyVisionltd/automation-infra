from contextlib import closing

from munch import Munch
import pymysql
import sshtunnel

import CONSTS
from infra.model import plugins


class Memsql(object):
    def __init__(self, host=Munch(ip='0.0.0.0', user='user', password='user1!')):
        self.tunnel = sshtunnel.open_tunnel(host.ip,
                                   ssh_username=host.user, ssh_password=host.password,
                                   remote_bind_address=(CONSTS.MEMSQL, CONSTS.MEMSQL_PORT))
        self.tunnel.start()
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    def _get_connection(self):
        connection = pymysql.connect(host='localhost',
                                     port=self.tunnel.local_bind_port,
                                     user='root',
                                     password='password',
                                     cursorclass=pymysql.cursors.DictCursor)

        return connection

    def upsert(self, query):
        with closing(self.connection.cursor()) as cursor:
            res = cursor.execute(query)
        self.connection.commit()
        return res

    def fetch_all(self, query):
        with closing(self.connection.cursor(pymysql.cursors.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchall()
        return res


plugins.register('Memsql', Memsql)
