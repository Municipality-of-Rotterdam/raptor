# {{ cookiecutter.package_name }}

################

**NB:** Add Azure DevOps CI/CD pipeline status badge:

Pipelines > {{ cookiecutter.repo_name }} > click on three dots in upper right corner > Status badge > Branch: develop > replace this instruction with a Sample markdown.

################

**NB:** Add Github CI/CD pipeline status badge:

[Github workflow status badge](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/adding-a-workflow-status-badge)

################


[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Give a description of your repository here.

## Installation

### Prerequisites

Install [direnv](https://direnv.net/) and add the hook to your shell:

```bash
# Install direnv
sudo apt-get install direnv   # Debian/Ubuntu

# Add to your shell profile (~/.bashrc)
eval "$(direnv hook bash)"     # bash
```

### Option A: Conda + uv (recommended for packages that need system libraries like GDAL)

```bash
# Create conda env (installs Python + uv at /anaconda/envs/{{ cookiecutter.package_name }})
conda env create --file environment.yml

# Allow direnv for this project (one-time)
direnv allow

# Activate the conda env and sync uv dependencies
conda activate {{ cookiecutter.package_name }}
uv sync --inexact                           # base dependencies (--inexact keeps conda packages)
uv sync --inexact --group dev               # include dev dependencies
uv sync --inexact --group dev --group test  # include dev + test dependencies
```

### Option B: uv only

```bash
# Allow direnv for this project (one-time)
direnv allow

# Sync dependencies (direnv auto-sets the environment path)
uv sync                           # base dependencies
uv sync --group dev               # include dev dependencies
uv sync --group dev --group test  # include dev + test dependencies
```

### Running commands

```bash
uv run pytest                      # run tests
uv run python -m {{ cookiecutter.package_name }}  # run your package
```

> **Note:** The `.envrc` file uses [direnv](https://direnv.net/) to automatically set `UV_PROJECT_ENVIRONMENT` when you enter this project directory. If a conda environment exists at `/anaconda/envs/{{ cookiecutter.package_name }}`, uv will install into it (use `--inexact` to keep conda packages). Otherwise, uv uses a local disk path at `~/.local/share/uv/envs/{{ cookiecutter.package_name }}`.

## Documentation

<!-- Replace the documentation_link to the documentation of your repository -->
You can find the documentation of this repository [on this website](documentation_link).

## Examples

Here you can give some examples. Here is an example to get you started:

```bash
from {{ cookiecutter.package_name }} import multiply
result = multiply(2, 3)
print(result)
```

This example shows how to use the multiply functionality within the repository.

## Resources

<!-- Replace the links to the corresponding urls of your repository -->
* [Releases](releases_link)
* [Documentation](documentation_link)
* [JIRA board](jira_link)