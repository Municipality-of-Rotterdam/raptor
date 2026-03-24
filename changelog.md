# Change Log: Raptor
All notable changes to this repo will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this repo adheres to [Semantic Versioning](http://semver.org/).

## [1.5.0] - 2026-03-05
Migrated from Poetry to uv.

### **Changed**
- Replaced pyproject.toml validation in CI/CD build pipeline with a `check-jsonschema` pre-commit hook using the PEP 621 schema
- Replaced Poetry with uv for dependency management, building, and running commands
- Converted `[tool.poetry.group.*]` dependency groups to PEP 735 `[dependency-groups]`
- Switched build backend from poetry-core to hatchling (package_repo template)
- Non-package projects now use `[tool.uv] package = false`
- Private index authentication via `UV_INDEX_*` environment variables and System.AccessToken
- GitHub workflows now use `astral-sh/setup-uv@v5`
- Cookiecutter variable `poetry_version` renamed to `uv_version`
- Pre-commit poetry-check/poetry-lock hooks replaced with `uv lock --check`
- Moved test dependencies from `tests/test_requirements.txt` to `[dependency-groups]` in pyproject.toml
- Split `azure-pipelines.yml` / `main.yml` into separate `ci.yml` (PR trigger) and `cd.yml` (merge trigger)
- CI/CD templates now install uv via standalone installer and Python via `uv python install`, removing the `UsePythonVersion` task and pip dependency
- Simplified CI/CD templates: merged separate `uv sync` + `uv run` steps into single `uv run --group <name>` calls where possible
- Environment setup now uses direnv (`.envrc`) for both conda+uv and uv-only workflows
- Replaced `tomlq` dependency with `tomllib` if python>=3.11 or `tomli` if python <3.11
- Updated `ipykernel` from pinned yanked version `6.21.0` to `>=6.21.1`
- Improved generated README with clear two-option setup guide (conda+uv vs uv-only)

### **Removed**
- `poetry-plugin-export` dependency from package_repo template
- `tests/test_requirements.txt` (consolidated into pyproject.toml)
- `azure-pipelines.yml` entry point from generated repos (replaced by separate ci/cd pipeline files)
- `scripts/setup_conda_uv_hooks.sh` and `scripts/setup_uv_env.sh` (replaced by direnv)

## [1.2.1] - 2026-02-12
Hotfix for getting tag refs for CI/CD templates.

## [1.2.0] - 2026-02-12
Centralized template hosting.

### **Changed**
- CI/CD pipeline templates now imported from remote repository (Raptor)

## [0.3.1] - 2025-10-21
Updated prompting for package publishing in case of Github.

### **Changed**
- Prompt now explicitly asks whether or not to publish to public pypi when working with Github.
- Added earlier devops fix to github for getting package version from pyproject.toml with regex.

## [0.3.0] - 2025-09-30
Updated test framework.

### **Changed**
- Test framework made minimal, showcasing basic testing features, without external dependencies.

## [0.2.0] - 2025-09-26
Removed the WikiGenerator keyvault from DevOps CI/CD pipelines.

### **Changed**
- The keys WikiId and WikiSecret are moved from the SharedKeyvault to the AmlProdGroup.

## [0.1.1] - 2025-08-28
Fix package repo ci/cd and remove double prompts.

### **Fixed**
- Fixed package repo ci/cd (whitespace issue in config.yml)
- Remove double prompts for name and email

## [0.1.0] - 2025-08-28
Rework project repo batch endpoint and scheduled pipeline.

### **Changed**
- Simplify creation of multiple environments or components by using for-loops
- Creating new project repo based on scheduled pipeline results in working aml pipelinejob (within GemeenteRotterdam environment)
- Use replacetokens devops extension replacing own ugly code
- Rearrange parts of batch endpoint and scheduled pipeline to prevent duplicate code
- Remove many parameters which already could be called as variable
### **Fixed**
- Update ChangedFiles devops extension to version 2

## [0.0.5] - 2025-08-19
Added support for publishing Sphinx doucmentation to github pages.

### **Added**
- Support for Sphinx documentation to github pages.
### **Fixed**
- Fixed main workflow with new pre-commit and unittest settings.

## [0.0.4] - 2025-07-21
Added support for supplying user config.

### **Added**
- Support for supplying a user config.
### **Fixed**
- Update to newest mcr.microsoft.com/azureml base image.
- author name including email bug

## [0.0.3] - 2025-07-09
Fixed file cleanup after conditional prompt. Added CI tests for Github repo variant.

### **Added**
- CI tests for Github repo variant
### **Fixed**
- File cleanup after conditional prompt now happens before committing the template files.

## [0.0.2] - 2025-07-09
CI/CD fixes.

### **Added**
- test_requirements.txt for github CI/CD
### **Changed**
- updated poetry and cookiecutter version in test_requirements.txt
### **Fixed**
- default input values for local_extensions.py
- repo_name default value for project_repo in CI
- package_feed prompting for project_repo
- cookiecutter.organisation_name variable


## [0.0.1] - 2025-07-08
First version of the Raptor cookiecutter template.