#!/usr/bin/env python3
from datetime import datetime
import re
import os
import sys
import time
import arrow
import shutil
from pathlib import Path
import json
import inquirer
import click
import subprocess
from . import cli
from .config import pass_config
from .config import Config

import subprocess

odoo_versions = [11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0]


@cli.command()
@pass_config
def ovm(config):
    pass


@cli.command()
def sample():
    click.secho(
        (
            "[name1]\n"
            "regex = *.dump.gz\n"
            "path = <remote path>\n"
            "host = <ssh host>\n"
            "destination = <here to put - a filename>\n"
        )
    )

