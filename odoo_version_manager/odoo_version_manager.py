#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import os
import sys
import subprocess
import inspect
import json
import click
from . import cli
from .config import pass_config
from .config import Config
from .repo import Repo
from .tools import _raise_error
from .consts import (
    odoo_versions,
    github_workflow_file,
    version_behind_main_branch,
    settings,
)
from .consts import gitcmd as git

current_dir = Path(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
)


class Settings(object):
    def __init__(self, root_path):
        self.root_path = root_path
        self.path = Path(root_path) / settings

    def get(self):
        if not self.path.exists():
            return {}
        content = self.path.read_text()
        return json.loads(content)

    def set(self, value):
        self.path.write_text(json.dumps(value, indent=4))

    def set_value(self, key, value):
        settings = self.get()
        settings[key] = value
        self.set(settings)


def _setup_main_version():
    vbmb = Path(version_behind_main_branch)
    if not vbmb.exists():
        _raise_error(
            f"File {vbmb} does not exist. Please create it first, e.g.: echo 18.0 > {vbmb}"
        )
    raw = vbmb.read_text().strip()
    try:
        main_version = float(raw)
    except ValueError:
        _raise_error(
            f"Invalid version in {vbmb}: {raw!r} (expected a number like 18.0)"
        )
    if main_version not in odoo_versions:
        _raise_error(
            f"Unknown Odoo version {main_version} in {vbmb}. Supported: {odoo_versions}"
        )
    os.environ["MAIN_VERSION"] = str(main_version)
    return main_version


def _get_source_branch(branch):
    branch = float(branch)
    main_version = float(os.environ["MAIN_VERSION"])
    if branch == main_version:
        return None  # root branch, no source
    elif branch < main_version:
        return branch + 1
    else:
        return branch - 1


def _create_branch(repo, branch):
    main_version = float(os.environ["MAIN_VERSION"])
    branch = float(branch)
    source_branch = _get_source_branch(branch)

    repo.checkout(str(source_branch), force=True)
    repo.X(*(git + ["checkout", "-b", str(branch)]))
    repo.X(*(git + ["push", "--set-upstream", "origin", str(branch)]))


def _get_mappings(current_branch):
    main_version = float(os.environ["MAIN_VERSION"])
    current_branch = float(current_branch)
    if current_branch < main_version:
        yield current_branch - 1, current_branch
    elif current_branch > main_version:
        yield current_branch + 1, current_branch
    else:
        # root branch: deploy to both direct neighbors
        if current_branch - 1 in odoo_versions:
            yield current_branch - 1, current_branch
        if current_branch + 1 in odoo_versions:
            yield current_branch + 1, current_branch


def _get_deploy_patches(current_branch):
    """
    mappings_source_dest: [(dest, source), (dest, source)] - like in assembler

    """
    mappings_source_dest = list(_get_mappings(current_branch))
    content = (current_dir / "deploy_patches.yml").read_text()
    mappings = []
    settings = Settings(os.getcwd()).get()
    for dest, source in mappings_source_dest:
        mappings.append(f"{dest}:{source}")
    for k, v in (
        {
            "<mappings>": " ".join(mappings),
            "<current_branch>": current_branch,
            # keep fallback in sync with default written by _check_default_settings
            "<settings.runs_on>": settings.get("runs_on", "ubuntu-latest"),
        }
    ).items():
        content = content.replace(k, str(v))

    return content


@cli.command()
@pass_config
@click.argument(
    "runner_label",
    required=False,
    type=click.Choice(
        ["self-hosted", "ubuntu-latest"],
        case_sensitive=False,
    ),
)
def setup(config, runner_label):
    _check_default_settings()
    S = Settings(os.getcwd())
    if runner_label:
        S.set_value("runs_on", runner_label)
    _process(config, edit=True, gitreset=True)


@cli.command()
@pass_config
@click.option(
    "-h",
    "--reset-hard",
    is_flag=True,
    help="Pulls and resets the local branch to match origin branch. Caution: all local data lost in local branches (backup is done before)",
)
def status(config, reset_hard):
    _check_default_settings()
    _process(config, edit=False, gitreset=reset_hard)


def _check_default_settings():
    s = Settings(os.getcwd())
    if not s.path.exists():
        click.secho(f"Creating default settings file: {s.path}", fg="yellow")
        s.path.parent.mkdir(parents=True, exist_ok=True)
        s.path.write_text('{"runs_on": "ubuntu-latest"}')


def _require_clean_repo(repo):
    if repo.all_dirty_files:
        _raise_error(f"Repo mustn't be dirty: {repo.all_dirty_files}")


def _get_github_branches_url(repo):
    try:
        url = repo.X(*(git + ["remote", "get-url", "origin"]), output=True).strip()
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):]
        if url.endswith(".git"):
            url = url[:-4]
        if "github.com" in url:
            return url + "/branches"
    except Exception:
        pass
    return None


def _check_no_main_branch(repo):
    all_branches = repo.get_all_branches()
    if "main" not in all_branches:
        return

    main_version = os.environ.get("MAIN_VERSION")
    has_drift = False
    commits_only_in_main = 0
    commits_only_in_version = 0

    if main_version:
        try:
            only_in_main = repo.X(
                *(git + ["log", "--oneline", f"{main_version}..main"]), output=True
            ).strip()
            only_in_version = repo.X(
                *(git + ["log", "--oneline", f"main..{main_version}"]), output=True
            ).strip()
            commits_only_in_main = len([l for l in only_in_main.splitlines() if l])
            commits_only_in_version = len([l for l in only_in_version.splitlines() if l])
            has_drift = commits_only_in_main > 0 or commits_only_in_version > 0
        except Exception:
            pass

    github_url = _get_github_branches_url(repo)

    click.secho("\n" + "=" * 60, fg="red")
    if has_drift and main_version:
        click.secho(
            f"  FEHLER: Branch 'main' existiert und hat Drift zu '{main_version}'!",
            fg="red", bold=True,
        )
        click.secho(f"  Commits nur in main:         {commits_only_in_main}", fg="red")
        click.secho(f"  Commits nur in {main_version}:  {commits_only_in_version}", fg="red")
    else:
        click.secho(
            "  WARNUNG: Branch 'main' existiert noch und muss gelöscht werden.",
            fg="yellow", bold=True,
        )
    click.secho("=" * 60, fg="red")
    click.secho("  → Lokal löschen:  git branch -D main", fg="yellow")
    click.secho("  → Remote löschen: git push origin --delete main", fg="yellow")
    if github_url:
        click.secho(f"  → GitHub Branches: {github_url}", fg="cyan")
    click.secho("=" * 60 + "\n", fg="red")
    sys.exit(-1)


def _check_main_version(edit):
    statusinfo = []
    vbmb = Path(version_behind_main_branch)
    vbmb_exists = vbmb.exists()
    if not vbmb_exists:
        statusinfo.append(
            ("yellow", f"File {vbmb} does not exist --> workflow not initialized")
        )
        if not edit:
            _raise_error(f"Please define version in {vbmb} e.g. echo 18.0 > {vbmb}")
    else:
        statusinfo.append(("green", f"File {vbmb} is set."))
    return statusinfo, vbmb_exists


def _checkout_version(repo, version, gitreset):
    all_branches = repo.get_all_branches()
    if version not in all_branches:
        return None
    repo.checkout(version, True)
    if gitreset:
        date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        repo.X(*(git + ["checkout", "-b", f"{version}-backup-{date}"]))
        repo.checkout(version, True)
        repo.X(*(git + ["reset", "--hard", f"origin/{version}"]))
    return True


def _update_gwf_file(repo, version):
    gwf = Path(github_workflow_file)
    content = _get_deploy_patches(str(version))
    gwf.parent.mkdir(parents=True, exist_ok=True)
    gwf.write_text(content)
    repo.X(*(git + ["add", gwf]))
    repo.X(
        *(
            git
            + [
                "commit",
                "--no-verify",
                "-m",
                "added workflow file for deploying subversion",
            ]
        )
    )
    try:
        repo.X(*(git + ["pull"]))
        repo.X(*(git + ["push"]))
    except subprocess.CalledProcessError:
        click.secho("Perhaps merge conflicts - fix git please", fg="red")
        repo.X(*(git + ["status"]))
        sys.exit(-1)


def _check_workflow(repo, version, edit):
    statusinfo = []
    gwf = Path(github_workflow_file)
    if not gwf.exists():
        statusinfo.append(
            ("yellow", f"File {gwf} does not exist --> workflow not initialized")
        )
        if edit:
            statusinfo.append(("green", f"creating missing {gwf} file"))
            _update_gwf_file(repo, version)
    else:
        statusinfo.append(("green", "Workflow initialized"))
        content = _get_deploy_patches(str(version))
        if gwf.read_text().strip() != content.strip():
            if edit:
                statusinfo.append(("green", f"Fixxing {gwf} file."))
                _update_gwf_file(repo, version)
            else:
                statusinfo.append(("red", "The content of the workflow mismatches."))
    return statusinfo


def _print_status(status):
    click.secho("----------------------------------", fg="red")
    for branch, info in sorted(status.items(), key=lambda x: x[0]):
        click.secho(f"Branch {branch}:", fg="green", bold=True)
        for color, line in info:
            click.secho("\t" + line, fg=color)


def _process(config, edit, gitreset):
    repo = Repo(os.getcwd())
    _require_clean_repo(repo)

    remember_branch = repo.get_branch()
    try:
        status = {}
        main_statusinfo, vbmb_exists = _check_main_version(edit)
        if vbmb_exists:
            _setup_main_version()
        status["config"] = main_statusinfo
        _check_no_main_branch(repo)
        repo.X(*(git + ["fetch", "--all"]))

        for version in list(map(str, odoo_versions)):
            statusinfo = []
            try:
                if _checkout_version(repo, version, gitreset) is None:
                    continue
            except Exception:
                statusinfo.append(("yellow", "Branch missing"))
                if edit:
                    _create_branch(repo, version)
                    statusinfo.append(("green", f"created branch {version}"))
                    repo.checkout(version)
                else:
                    status[version] = statusinfo
                    continue
            statusinfo.append(("green", "Branch exists"))
            if vbmb_exists:
                statusinfo += _check_workflow(repo, version, edit)
            status[version] = statusinfo

        _print_status(status)
    finally:
        repo.checkout(remember_branch, force=True)


@cli.command()
@pass_config
@click.option(
    "-r",
    "--remove-intermediate-commits",
    help="Makes rebase interactive to reduce amount of commits.",
    is_flag=True,
)
def rebase(config, remove_intermediate_commits):
    repo = Repo(os.getcwd())
    _require_clean_repo(repo)
    main_version = _setup_main_version()
    _check_no_main_branch(repo)

    # run upward
    for version in map(str, odoo_versions):
        if float(version) >= main_version:
            _rebase_branch(repo, version, remove_intermediate_commits)

    # run downward
    for version in map(str, reversed(odoo_versions)):
        if float(version) < main_version:
            _rebase_branch(repo, version, remove_intermediate_commits)


def _rebase_branch(repo, branch, remove_intermediate_commits):
    source_branch = _get_source_branch(branch)
    if source_branch is None:
        click.secho(f"  Skipping {branch} (root branch, no rebase source)", fg="cyan")
        return
    repo.checkout(branch, force=True)
    repo.X(*(git + ["pull"]))
    try:
        repo.X(*(git + ["rebase", str(source_branch)]))
    except subprocess.CalledProcessError:
        _handle_rebase_conflict(repo, branch)
    else:
        repo.X(*(git + ["push", "-f"]))

    if remove_intermediate_commits:
        _squash_intermediate_commits(repo, branch)


def _handle_rebase_conflict(repo, branch):
    gwf = Path(github_workflow_file)
    gwf.write_text(_get_deploy_patches(branch))
    try:
        repo.X(*(git + ["add", str(gwf)]))
    except subprocess.CalledProcessError:
        pass
    repo.X(*(git + ["status"]))
    click.secho("Please merge changes then:", fg="yellow")
    click.secho("git rebase --continue")
    click.secho("git push -f")
    sys.exit(-1)


def _squash_intermediate_commits(repo, branch):
    source_branch2 = _get_source_branch(branch)
    if source_branch2 is None:
        return
    commitsha = repo.X(
        *(git + ["merge-base", branch, str(source_branch2)]), output=True
    ).strip()
    count = repo.X(
        *(git + ["rev-list", "--count", f"{commitsha}..{branch}"]), output=True
    ).strip()
    if count not in ("0", "1"):
        click.secho(
            "Please squash all lines except first one.\nAnd push: git push -f\nWhen done please redo the rebase of the odoo version manager.",
            fg="yellow",
        )
        repo.X(*(git + ["rebase", "-i", commitsha]))
        sys.exit(-1)
