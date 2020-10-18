import logging
import sys
from rpyc.utils.server import ThreadedServer


def start_service(port, loglevel, service):
    ch = logging.StreamHandler(sys.stdout)
    logging.basicConfig(level=loglevel, format='%(relativeCreated)6d %(threadName)s %(message)s', handlers=[ch])
    server = ThreadedServer(service, hostname="0.0.0.0", port=port, protocol_config={"allow_public_attrs": True,
                                                                                     "allow_getattr" : True,
                                                                                     "allow_all_attrs": True,
                                                                                     "allow_pickle" : True})
    server.start()
