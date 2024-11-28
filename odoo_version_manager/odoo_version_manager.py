#!/usr/bin/env python3
from pathlib import Path
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
from .repo import Repo
from .tools import _raise_error
from .consts import odoo_versions, github_workflow_file, version_behind_main_branch
import subprocess
import inspect
import os
from pathlib import Path
from .consts import gitcmd as git

current_dir = Path(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
)


def _create_branch(repo, branch):
    main_version = float(os.environ["MAIN_VERSION"])
    branch = float(branch)

    if branch < main_version:
        source_branch = branch + 1
    elif branch == main_version:
        source_branch = main_version
    else:
        source_branch = branch - 1
    repo.checkout(str(source_branch), force=True)
    repo.X(*(git + ["checkout", "-b", str(branch)]))
    repo.X(*(git + ["push", "--set-upstream", "origin", str(branch)]))


def _get_mappings(current_branch):
    vbmb = Path(version_behind_main_branch)
    main_version = float(os.environ["MAIN_VERSION"])
    if current_branch == "main":
        yield main_version - 1, "main"
        yield main_version + 0, "main"
        yield main_version + 1, "main"
    else:
        current_branch = float(current_branch)
        if current_branch < main_version:
            yield current_branch - 1, current_branch
        elif current_branch > main_version:
            yield current_branch + 1, current_branch


def _get_deploy_patches(current_branch):
    """
    mappings_source_dest: [(dest, source), (dest, source)] - like in assembler

    """
    mappings_source_dest = list(_get_mappings(current_branch))
    content = (current_dir / "deploy_patches.yml").read_text()
    mappings = []
    for dest, source in mappings_source_dest:
        mappings.append(f"{dest}:{source}")
    content = content.replace("<mappings>", " ".join(mappings))
    content = content.replace("<current_branch>", current_branch)
    return content


@cli.command()
@pass_config
def setup(config):
    _process(config, edit=True)


@cli.command()
@pass_config
def status(config):
    _process(config, edit=False)


def _process(config, edit):
    repo = Repo(os.getcwd())
    if repo.all_dirty_files:
        _raise_error(f"Repo mustn't be dirty: {repo.all_dirty_files}")

    remember_branch = repo.get_branch()
    try:

        status = {}
        statusinfo = []
        repo.checkout("main", force=True)
        vbmb = Path(version_behind_main_branch)
        vbmb_exists = vbmb.exists()
        if not vbmb.exists():
            statusinfo.append(
                "yellow", f"File {vbmb} does not exist --> workflow not initialized"
            )
            if not edit:
                _raise_error(f"Please define version in {vbmb}")
        else:
            statusinfo.append(("green", f"File {vbmb} is set."))
            main_version = float(str(float(vbmb.read_text().strip())))
            os.environ["MAIN_VERSION"] = str(main_version)
        status["main"] = statusinfo

        for version in map(str, odoo_versions):
            statusinfo = []
            try:
                repo.checkout(version)
            except:
                statusinfo.append(("yellow", "Branch missing"))
                if edit:
                    _create_branch(repo, version)
                    statusinfo.append(("green", f"created branch {version}"))
                    repo.checkout(version)
                else:
                    status[version] = statusinfo
                    continue
            statusinfo.append(("green", "Branch exists"))
            if not vbmb_exists:
                continue

            gwf = Path(github_workflow_file)

            def _update_gwf_file():
                content = _get_deploy_patches(str(version))
                gwf.parent.mkdir(parents=True, exist_ok=True)
                gwf.write_text(content)
                repo.X(*(git + ["add", gwf]))
                repo.X(
                    *(
                        git
                        + [
                            "commit",
                            "-m",
                            "added workflow file for deploying subversion",
                        ]
                    )
                )
                repo.X(*(git + ["push"]))

            if not gwf.exists():
                statusinfo.append(
                    (
                        "yellow",
                        f"File {gwf} does not exist --> workflow not initialized",
                    )
                )
                if edit:
                    statusinfo.append(("green", "creating missing {gwf} file"))
                    _update_gwf_file()

            else:
                statusinfo.append(("green", "Workflow initialized"))

                content = _get_deploy_patches(str(version))
                content_ok = gwf.read_text().strip() == content.strip()
                if not content_ok:
                    if edit:
                        statusinfo.append(("green", f"Fixxing {gwf} file."))
                        _update_gwf_file()
                    else:
                        statusinfo.append(
                            ("red", "The content of the workflow mismatches.")
                        )

            status[version] = statusinfo

        click.secho("----------------------------------", fg="red")
        for branch, info in sorted(status.items(), key=lambda x: x[0]):
            click.secho(f"Branch {branch}:", fg="green", bold=True)
            for line in info:
                color, line = line
                click.secho("\t" + line, fg=color)

    finally:
        repo.checkout(remember_branch, force=True)
