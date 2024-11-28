import atexit
import click
import logging
from pathlib import Path
import sys
import json
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
        self.sources = {}
        self.source = None
        if BASE_PATH.exists():
            for file in BASE_PATH.glob("*"):
                if file.name.startswith('.'):
                    continue
                for section, config in self.parse_file(file):
                    self.sources[section] = config

        def cleanup():
            pass

        atexit.register(cleanup)

    def parse_file(self, file):
        config = configparser.ConfigParser()
        config.read(file)
        for section in config.sections():
            yield (section, config[section])

    @contextmanager
    def shell(self):
        config = self.get_source()

        def execute(cmd):
            output = subprocess.check_output([
                "ssh", config['host'],
            ] + cmd)
            output = output.decode('utf-8').split("\n")
            return output

        yield config, execute

    def add(self, filename, host, username, path, regex, destination):
        path = BASE_PATH / Path(filename).name
        config = configparser.ConfigParser()
        BASE_PATH.mkdir(exist_ok=True, parents=True)
        if path.exists():
            config.read(path)
        config[self.source] = {
            "host": host,
            "path": path,
            "regex": regex,
            "destination": destination,
        }
        if username:
            config[self.source]['username'] = username
        with open(path, 'w') as configfile:
            config.write(configfile)

    def get_source(self):
        if not self.source:
            raise Exception("Please define a source first!")
        return self.sources[self.source]

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
