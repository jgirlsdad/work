import logging
import os.path
import time
import sys


def setup(title):
    logger = logging.getLogger(title)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(os.path.join(os.getenv('bic_etl_home'),
                                       'general', 'logs', 'log.json'))
    formatter = logging.Formatter('''{"name": "%(name)s","pid": "%(process)d", "level": "%(levelno)s", "msg": "%(message)s", "time": "%(asctime)s"}''')
    formatter.converter = time.gmtime
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    return logger

def setupNew(title):
    logger = logging.getLogger(title)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(os.path.join(os.getenv('bic_etl_home'),
                                       'general', 'logs', 'log.json'))
    formatter = logging.Formatter('''{"name": "%(name)s","4x4": "%(s4x4)s", "pid": "%(process)d", "level": "%(levelno)s", "msg": "%(message)s", "time": "%(asctime)s"}''')
    formatter.converter = time.gmtime
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    return logger
