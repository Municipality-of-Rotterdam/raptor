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

This project uses [uv](https://github.com/astral-sh/uv) for Python package management. `UV_PROJECT_ENVIRONMENT` is used to store the virtual environment on local disk rather than on a network mount.

Choose **one** of the three setup options below.

### Option 1: direnv (recommended)

Uses the `.envrc` file to auto-set `UV_PROJECT_ENVIRONMENT` when you `cd` into the project. Works for both conda + uv and uv-only.

```bash
# Install direnv (one-time)
sudo apt-get install direnv   # Debian/Ubuntu

# Add to your shell profile (~/.bashrc, one-time)
eval "$(direnv hook bash)"

# Allow direnv for this project (one-time per clone)
direnv allow
```

Then continue with either [Conda + uv](#conda--uv) or [uv only](#uv-only) below.

### Option 2: Conda + uv with activate hooks

No extra tools needed. Sets `UV_PROJECT_ENVIRONMENT` automatically when you `conda activate`.

```bash
# Create conda env (one-time)
conda env create --file environment.yml

# Install activate/deactivate hooks (one-time)
./scripts/setup_conda_uv_hooks.sh
```

Then continue with [Conda + uv](#conda--uv) below.

### Option 3: uv only with activate script

No extra tools needed. Creates the environment on local disk and generates an activate script.

```bash
# Set up environment and create activate script (one-time)
./scripts/setup_uv_env.sh
```

Then continue with [uv only](#uv-only) below.

---

### Conda + uv

Recommended when you need system libraries (e.g. GDAL) that are only available via conda.

```bash
# Create conda env if not done above (installs Python + uv at /anaconda/envs/{{ cookiecutter.package_name }})
conda env create --file environment.yml

# Activate the conda env
conda activate {{ cookiecutter.package_name }}

# Open new terminal or cd away and back to project root
cd ..
cd {{ cookiecutter.repo_name }}

# Sync uv dependencies (--inexact keeps conda packages)
uv sync --inexact                           # base dependencies
uv sync --inexact --group dev               # include dev dependencies
uv sync --inexact --group dev --group test  # include dev + test dependencies
```

### uv only

```bash
# Activate the environment (not needed if using direnv)
source activate.sh

# Sync dependencies
uv sync                           # base dependencies
uv sync --group dev               # include dev dependencies
uv sync --group dev --group test  # include dev + test dependencies
```

### Running commands

```bash
uv run pytest                      # run tests
uv run python -m {{ cookiecutter.package_name }}  # run your package
```

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