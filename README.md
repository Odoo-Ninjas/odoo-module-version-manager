# odoo-version-manager

Helps handling updates on main branch of a module to be deployed to all sub branches.
It uses github workflows to accomplish this.

## installing

```bash
pipx install odoo-version-manager
odoo-version-manager completion -x
```

# usage

## initial setup

- create a repository like an OCA repository with some modules on branch **main**
- decide which version the main branch is for example 16.0 and store it:

```bash
echo 16.0 > .github/version_behind_main_branch
odoo-version-manager setup
```

`setup` takes an optional runner label for the generated github workflow
(`self-hosted` or `ubuntu-latest`, default: `ubuntu-latest`):

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

## set another odoo version for main branch

If you move on and main branch becomes odoo version 18.0 instead of 16.0 do the following:

```
git checkout main
git reset --hard origin/18.0
vi .github/version_behind_main_branch and set 18.0 there
odoo-version-manager setup
```

## rebase all branches

If there are merge conflicts you must manually help the branches to pass there new commits from one to the other.
It is advised to use the -r option to reduce the commits from one branch to the other to make it easier the next time to resolve merge conflicts.

```
odoo-version-manager rebase -r
```
