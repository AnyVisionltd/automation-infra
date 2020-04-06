"""
general settings / logger
"""
import logging

# pylint: disable=C0103
log = logging.getLogger("app")
chan = logging.StreamHandler()
log.setLevel(logging.DEBUG)
chan.setLevel(logging.DEBUG)
chan.setFormatter(logging.Formatter(
    "[L:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
))
log.addHandler(chan)
