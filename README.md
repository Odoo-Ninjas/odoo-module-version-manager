# odoo-version-manager

Manages Odoo modules across multiple version branches (11.0–19.0).
Changes on the root version branch are automatically deployed to all other branches via GitHub Actions + rebase.

There is **no `main` branch** — the versioned branch (e.g. `16.0`) is the direct source of truth.
The branch chain looks like this:
```
11.0 ← 12.0 ← ... ← 16.0 (root) ← 17.0 ← ... ← 19.0
```

## installing

```bash
pipx install odoo-version-manager
odoo-version-manager install-completion
```

# usage

## initial setup

- create a repository with your modules on the root version branch (e.g. `16.0`)
- define which version is the root:

```bash
mkdir -p .github
echo 16.0 > .github/version_behind_main_branch
odoo-version-manager setup
```

`setup` takes an optional runner label for the generated github workflow
(`self-hosted` or `ubuntu-latest`, default: `ubuntu-latest`). It is stored
persistently in the settings file:

```bash
odoo-version-manager setup self-hosted
```

## settings file

Settings are stored per repository in `.github/odoo-version-manager.settings.json`
(created automatically on first run):

```json
{"runs_on": "ubuntu-latest"}
```

- `runs_on`: runner label used in the generated deploy workflow. Use
  `self-hosted` if the `SSH_PRIVATE_KEY` secret should never leave your own
  infrastructure.

The generated workflow requires the repository secret `SSH_PRIVATE_KEY` to
push to the version branches.

## upgrade root version

If you want to move the root version from 16.0 to 18.0:

```bash
git checkout 18.0
echo 18.0 > .github/version_behind_main_branch
odoo-version-manager setup
```

## rebase all branches

If there are merge conflicts you must manually help the branches to pass their new commits from one to the other.
It is advised to use the -r option to reduce the commits from one branch to the other to make it easier the next time to resolve merge conflicts.

```
odoo-version-manager rebase -r
```

## existing `main` branch

If a `main` branch still exists in the repository, the tool will refuse to run and display instructions on how to delete it. A `main` branch is no longer used and causes confusion.
