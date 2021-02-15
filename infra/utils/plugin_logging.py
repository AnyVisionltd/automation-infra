import logging


def configure_cli_logging(config):
    config.option.log_format = '%(asctime)s.%(msecs)0.3d %(threadName)-10.10s %(levelname)-6.6s %(message)s %(funcName)-15.15s %(pathname)s:%(lineno)d'
    config.option.log_cli_format = config.option.log_format

    config.option.log_file_date_format = '%Y-%m-%d %H:%M:%S'
    config.option.log_cli_date_format = config.option.log_file_date_format


class InfraFormatter(logging.Formatter):
    def __init__(self):
        msg_fmt = "%(asctime)20.20s.%(msecs)d %(threadName)-10.10s %(levelname)-6.6s %(message)-75s " \
              "%(funcName)-15.15s %(pathname)-70s:%(lineno)4d"
        logging.Formatter.__init__(self, msg_fmt, datefmt='%Y-%m-%d %H:%M:%S')