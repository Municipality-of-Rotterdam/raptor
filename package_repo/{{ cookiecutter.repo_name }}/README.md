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

This project uses [uv](https://github.com/astral-sh/uv) for Python package management, optionally combined with [conda](https://docs.conda.io/) for system-level libraries, and [direnv](https://direnv.net/) to automatically configure the environment.

There are **two setup options**:

| | Conda + uv | uv only |
|---|---|---|
| **Use when** | You need system libraries (e.g. GDAL, PROJ) only available via conda | Pure Python dependencies are sufficient |
| **Environment location** | `/anaconda/envs/{{ cookiecutter.package_name }}` | `~/.local/share/uv/envs/{{ cookiecutter.package_name }}` |
| **Sync command** | `uv sync --inexact` (keeps conda packages) | `uv sync` |

Both options require direnv and the `.envrc` file included in this project. The `.envrc` auto-detects which option you're using and sets `UV_PROJECT_ENVIRONMENT` accordingly, so uv installs packages to local disk rather than a network mount.

### Prerequisites: install uv and direnv

```bash
# Install uv (one-time, skip if already present)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install direnv (one-time)
sudo apt-get install direnv   # Debian/Ubuntu

# Add the hook to your shell profile (one-time, will skip if already present)
grep -qF 'direnv hook bash' ~/.bashrc || echo 'eval "$(direnv hook bash)"' >> ~/.bashrc

# Reload shell for changes to take effect
source ~/.bashrc

# It will say that .envrc is blocked.
# Run the following to approve it (one-time per clone):
direnv allow
```

### Option A: Conda + uv

Use this option when you need system-level libraries that are only available via conda.

```bash
# 1. Create the conda environment (installs Python + uv)
conda env create --file environment.yml

# 2. Activate the conda environment
conda activate {{ cookiecutter.package_name }}

# 3. Re-enter the project directory so direnv picks up the conda env path
cd .. && cd {{ cookiecutter.repo_name }}

# 4. Install Python dependencies with uv (--inexact keeps conda packages intact)
uv sync --inexact --group dev
```

### Option B: uv only

Use this option when you only need pure Python dependencies. No conda required.

```bash
# 1. Re-enter the project directory (or open a new terminal) so direnv sets the environment
cd .. && cd {{ cookiecutter.repo_name }}

# 2. Install Python dependencies with uv
uv sync --group dev
```

### Managing dependencies

Add a package to the project (optionally into a dependency group):

```bash
uv add <package>                        # add to [project.dependencies]
uv add --group dev <package>            # add to [dependency-groups] dev
```

Sync one or more dependency groups:

```bash
uv sync --group dev --group test        # dev + test dependencies
```

> **Note:** When using conda + uv, always pass `--inexact` to preserve conda-installed packages.

### Adding private package dependencies  [devops-only]

This project is configured with a private Azure Artifacts feed (`{{ cookiecutter.package_feed }}`). The index is marked `explicit = true`, meaning packages will only be resolved from it when explicitly pinned.

#### Authenticating with the private feed

In CI/CD, authentication is handled automatically via `System.AccessToken`. For local development, create a `~/.netrc` file with a Personal Access Token (PAT) from Azure DevOps:

```
machine pkgs.dev.azure.com
login <your-devops-email>
password <your-pat>
```

To create a PAT: Azure DevOps → User Settings → Personal Access Tokens → New Token → grant the **Packaging (Read)** scope.

#### Adding a private package

Because the feed is marked `explicit = true`, uv will not search it unless a package is explicitly pinned to it. You must add the source entry **before** adding the package, otherwise uv won't find it.

1. Pin the package to the private index by adding a `[tool.uv.sources]` entry in `pyproject.toml`:

    ```toml
    [tool.uv.sources]
    <package-name> = { index = "{{ cookiecutter.package_feed }}" }
    ```

2. Add and install the dependency:

    ```bash
    uv add <package-name>
    ```

### Running commands

```bash
uv run pytest                                    # run tests
uv run python -m {{ cookiecutter.package_name }}  # run your package
```

## Documentation

<!-- Replace the documentation_link to the documentation of your repository -->
You can find the documentation of this repository [on this website](documentation_link).

## Examples

Here you can give some examples. Here is an example to get you started:

```python
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
