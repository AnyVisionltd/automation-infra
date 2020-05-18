import logging
import sys
import logging.handlers as handlers
from enum import Enum

RESET_SEQ = "\033[0m"

class Color(Enum):
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    BLUE = '\033[34m'
    LIGHT_GREEN = '\033[92m'
    NORMAL_COLOR = '\033[39m'
    WHITE = '\033[37m'
    MAGENTA = '\033[35m'
    LIGHT_BLUE = '\033[94m'


COLORS = {
    'WARNING': Color.YELLOW,
    'CRITICAL': Color.RED,
    'ERROR': Color.RED,
}


class NormalFormatter(logging.Formatter):
    def __init__(self):
        msg = NormalFormatter.get_format_str()
        logging.Formatter.__init__(self, msg)

    @staticmethod
    def get_format_str():
        return "%(asctime)s %(process)d %(thread)d %(levelname)s %(name)s "\
               "%(message)s %(funcName)s %(pathname)s:%(lineno)d"


class ColoredFormatter(logging.Formatter):
    def __init__(self):
        msg = "%(asctime)s %(process)d %(thread)d %(start_color)s %(levelname)s %(name)s "\
              "%(message)s %(end_color)s %(funcName)s %(pathname)s:%(lineno)d"
        logging.Formatter.__init__(self, msg)

    def format(self, record):
        levelname = record.levelname
        custom_color = record.args.get('colorize_record', None) if isinstance(record.args, dict) else None
        if custom_color is None:
            record.start_color = COLORS[levelname].value if levelname in COLORS else ''
        else:
            record.start_color = custom_color.value
        record.end_color = RESET_SEQ
        return logging.Formatter.format(self, record)

def configure_console_logging(use_color=True, level=logging.INFO):
    logger = logging.getLogger()
    formatter = ColoredFormatter() if use_color else NormalFormatter()
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def configure_file_logging(filename,
                           level=logging.INFO,
                           backupCount=100000):
    logger = logging.getLogger()
    file_handler = handlers.RotatingFileHandler(filename, maxBytes=50000000, backupCount=backupCount)
    file_handler.setLevel(level)
    file_handler.setFormatter(NormalFormatter())
    logger.addHandler(file_handler)
    return logger

def configure_logging(root_level=logging.INFO,
                      console_level=logging.INFO,
                      file_level=logging.INFO,
                      filename=None):

    log = logging.getLogger()
    log.setLevel(root_level)
    if file_level != logging.NOTSET and filename is not None:
        configure_file_logging(filename, file_level)
    if console_level != logging.NOTSET:
        configure_console_logging(level=console_level)
    return log
