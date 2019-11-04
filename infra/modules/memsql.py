from contextlib import closing

import pymysql
import sshtunnel

import CONSTS
from infra.model import plugins


class Memsql(object):
    def __init__(self, host, memsql_host=CONSTS.MEMSQL, memsql_port=CONSTS.MEMSQL_PORT):
        # self._host = host
        # self._memsql_host = memsql_host
        # self._memsql_port = memsql_port
        self.tunnel = sshtunnel.open_tunnel(host.ip,
                                   ssh_username=host.user, ssh_password=host.password,
                                   remote_bind_address=(memsql_host, memsql_port))
        self.tunnel.start()

    def _get_connection(self):
        connection = pymysql.connect(host='localhost',
                                         port=self.tunnel.local_bind_port,
                                         user='root',
                                         password='password',
                                         cursorclass=pymysql.cursors.DictCursor)

        return connection

    def upsert(self, query):
        conn = self._get_connection()
        with closing(conn.cursor()) as cursor:
            res = cursor.execute(query)
        conn.commit()
        return res

    def fetch_all(self, query):
        conn = self._get_connection()
        with closing(conn.cursor(pymysql.cursors.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchall()
        return res


plugins.register('Memsql', Memsql)
