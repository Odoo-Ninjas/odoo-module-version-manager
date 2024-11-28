import click
import subprocess
import os
import sys
from pathlib import Path
from .config import pass_config
from .config import Config
import shellingham
from click_default_group import DefaultGroup

global_data = {
    'config': None
}

@click.group()
@pass_config
def cli(config):
    global_data['config'] = config



@cli.command()
def install_completion():
    def setup_for_shell_generic(shell, shell_call):
        path = Path(f"/etc/{shell}_completion.d")
        NAME = shell_call.upper().replace("-", "_")
        completion = subprocess.check_output([sys.argv[0]], env={f"_{NAME}_COMPLETE": f"{shell}_source"}, shell=True)
        if path.exists():
            if os.access(path, os.W_OK):
                (path / shell_call).write_bytes(completion)
                return

        if not (path / shell_call).exists():
            rc = Path(os.path.expanduser("~")) / f'.{shell}rc'
            if not rc.exists():
                return
            complete_file = rc.parent / f'.{shell_call}-completion.sh'
            complete_file.write_bytes(completion)
            if complete_file.name not in rc.read_text():
                content = rc.read_text()
                content += '\nsource ~/' + complete_file.name
                rc.write_text(content)

    name = Path(sys.argv[0]).name
    setup_for_shell_generic(shellingham.detect_shell()[0], name)
    sys.exit(0)

from . import odoo_version_manager
from . import gitcommands
from . import repo