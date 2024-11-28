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
- decide which version the main branch is for example 16.0

```
odoo-version-manager setup 16.0
```

## set another odoo version for main branch

If you move on and main branch becomes odoo version 18.0 instead of 16.0 do the following:

```
git checkout main
git reset --hard origin/18.0
odoo-version-manager setup 18.0
```
