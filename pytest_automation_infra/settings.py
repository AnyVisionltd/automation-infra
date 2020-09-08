import logging
import os


def init_infra_logger():
    log_fmt = '%(asctime)s.%(msecs)0.3d %(threadName)-10.10s %(levelname)-6.6s %(message)s %(funcName)-15.15s %(pathname)s:%(lineno)d'
    infra_logger = logging.getLogger('infra')
    os.makedirs('logs', exist_ok=True)
    fh = logging.FileHandler(f'logs/infra.log', mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(log_fmt))
    infra_logger.addHandler(fh)
    infra_logger.setLevel(logging.DEBUG)
    return infra_logger


infra_logger = init_infra_logger()