import atexit
import click
import logging
from pathlib import Path
import sys
import os
from contextlib import contextmanager
import configparser
from paramiko.config import SSHConfig
import subprocess

BASE_PATH = Path(os.path.expanduser("~/.fetch_latest_file.d"))
SSH_CONFIG = Path(os.path.expanduser("~/.ssh/config"))

class Config(object):
    def __init__(self):
        super().__init__()

        def cleanup():
            pass

        atexit.register(cleanup)

    def setup_logging(self):
        FORMAT = '[%(levelname)s] %(asctime)s %(message)s'
        formatter = logging.Formatter(FORMAT)
        logging.basicConfig(format=FORMAT)
        self.logger = logging.getLogger('')  # root handler
        self.logger.setLevel(self.log_level)

        stdout_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stdout_handler)
        stdout_handler.setFormatter(formatter)


pass_config = click.make_pass_decorator(Config, ensure=True)
