---
layout: default
title: Readme
---

# Raptor

![build status](https://github.com/Municipality-of-Rotterdam/raptor/actions/workflows/main.yml/badge.svg?branch=feature/github_actions)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

![Raptor](raptor_logo.png)

# RAPToR – Rapid Analytics Product Template of Rotterdam

This repository is a cookiecutter template to be used for projects in Azure Machine Learning.


# Table of Content
1. [Introduction](#introduction)
2. [Repository templates](#repository-templates)
3. [Repository setup](#repository-setup)
4. [Environment setup](#environment-setup)
5. [Continuous Integration](#continuous-integration)
6. [Writing code](#writing-code)
7. [Running code in Azure Machine Learning](#running-code-in-azure-machine-learning)
8. [Ecosystem/resource requirements and setup](#ecosystemresource-requirements-and-setup)
9. [Resources](#resources)
9. [Known Issues](#known-issues)
9. [License](#license)

## Introduction

This document will guide you through setting up your repository, configuring your development environment, and managing dependencies with Conda and Poetry.
This document supports two types of repository templates used in AzureML projects:

- Package Repository: for developing and maintaining reusable Python packages (mainly .py files)
- Project Repository: for orchestrating machine learning projects and pipelines (mainly .yml files)

## Repository templates

Both repository templates serve a specific purpose and follow best practices to ensure maintainability, scalability, and efficient collaboration between data scientists and ML engineers. Below, we outline the structure, usage, and CI/CD setup for both repository types.
A package repo is focused on a single package, usually used in a component.
A project repo can contain multiple components, each with a separate environment and compute specs.
These components are connected in a pipeline, and/or deployed as endpoints, and may be reused in other projects.

#### 2.1. Package Repository
The package_repo is intended for developing a package, sharing it with other developers (for further development), and publishing it for use in AzureML environments. 
The CI/CD process here focuses on testing, formatting, linting the code, publishing the package to artifacts, and creating an AzureML environment based on the package.

- Mainly for Data Scientists
- Contains a package with one or more modules (the folders inside the src directory)
- Uses a Poetry environment to manage dependencies
- CI: Unit tests, pre-commit hooks
- CD: Publishes package to Artifacts, registers the environment
- Follows best practices for production-ready code
- Contains Python scripts with classes and functions, but no if __name__ == "__main__" or argparse scripts
- The package is a collection of functions for the same subject with the same dependencies.

It is recommended to create generic reusable packages that support a specific technique (e.g., image_tiling) rather than making project-specific packages.

#### 2.2. Project Repository
The project_repo is intended to orchestrate a project. Here, all components (developed as separate packages in standalone repositories along with their respective environments) are defined and combined into a pipeline. 
The CI/CD process focuses on deploying the pipeline (possibly with an endpoint or other ML solution patterns—contact an ML engineer).
Code integration can be tested locally, but the required environment for the combined steps (including all dependencies) may become too large.

- Mainly for ML Engineers
- Main repository of a project containing all components but no developed Python code
- Contains components with if __name__ == "__main__" and argparse scripts
- Contains pipelines
- May include code to run multiple components as a pipeline locally
- Supports various deployment types for different solution patterns (e.g., batch endpoint, online endpoint, scheduled deployment)
- No CI, as there is no developed Python code
- CD: Creates endpoints and deploys pipelines

Thus, this repository does not contain a src directory and has as little Python code as possible.
The reason for this is that code in a Python package (src) is much easier to work with when using pre-commit hooks/unit tests, and having multiple such packages within a single repository can cause unnecessary complexity.

#### 2.3. Way of Working
If a project is in the Proof of Concept (POC) or Exploratory Data Analysis (EDA) phase, or if it involves a one-time or ad hoc delivery, you should focus on achieving results as quickly as possible (preferably within one sprint).
In such cases, you should only use the project repository, working with notebooks and draft Python code/scripts.
You create an environment manually using Conda and Pip.
Once the project scales up to a Pilot/Production phase, you follow the best practices of the project repo and package repo.

For each project, you will ultimately have one project repository and one or more package repositories.
Typically, you use one package per component. Data scientists can use the project repository as the main repository and clone package repositories as submodules to develop them.

## Repository setup

After completing this section, you will be able to connect to your repository via your personal compute instance. Moreover, you will have enabled  Continuous Integration (CI) and Continuous Deployment (CD) on your repository! Note that you will encounter: "YOUR_PACKAGE_NAME" sometimes in this section, it is simply a placeholder name of the repository you will be creating, replace it by the name of your repository.

#### 3.1. Connecting to your repository

If your compute instance does not have an ssh key stored on devops (SSH public keys under user settings),
you need to do this to be able to connect via ssh instead of https.

To generate an ssh key on the compute instance, open a terminal (in VSCode or through the Azure portal) and run:
```bash
ssh-keygen
```
The command produces a private key (id_rsa) and a public key (id_rsa.pub) in the /home/azureuser/.ssh/ folder.
Make sure that the private key stays private and only communicate the public key!
To access the public key, type:
```bash
cat /home/azureuser/.ssh/id_rsa.pub
```
Copy the displayed string.

##### 3.1.1 DevOps

To register the ssh key in DevOps:
- log in to DevOps and go to user settings > SSH public keys
- click the Add button, the "Add an SSH public key" dialogue opens
- Enter a description, for example "Azure compute instance <your_instance>"
- In the Key Data field, paste the copied public key string and press Save
Now your compute instance is able to communicate with the code repositories on DevOps.

For more info on setting up SSH on DevOps, click [here](https://learn.microsoft.com/en-us/azure/devops/repos/git/use-ssh-keys-to-authenticate?view=azure-devops)

##### 3.1.2 Github

For setting up an SSH connection on github, click
[here](https://docs.github.com/en/enterprise-server@3.12/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)

#### 3.2. Create the repo, using the raptor's url (it's recommended to use SSH)

Optionally, if cookiecutter is not yet installed in the base environment, run
```bash
pip install cookiecutter
```
Using your terminal, navigate to your user folder within the compute instance (home/azureuser/cloudfiles/code/Users/<username>)
There are two types of repos, as outlined in the Introduction above. You can either create a package repo or a project repo.
Create the repo (when using SSH, copy in the SSH clone URL), in this example a package repository:
```bash
cookiecutter <raptor_repo_url> --directory package_repo
```
If you want to create a repo from a specific raptor branch or tag, run e.g.
```bash
cookiecutter <raptor_repo_url> -c <branch or tag name> --directory package_repo
```
You can also supply a user config .yaml file with default values being set. 
You should set env variable COOKIECUTTER_CONFIG to your configuration file:
```bash
export COOKIECUTTER_CONFIG=path/to/config.yml
```
with schema e.g.
```yaml
default_context: 
    organisation_name: "MyOrg"
    package_feed: "MyFeed"
    additional_prompts: "devops"
```

If you want to run noninteractively, run
```bash
COOKIECUTTER_NO_INPUT=1 cookiecutter <raptor_repo_url> --no-input --directory package_repo
```
Extra input args can be set like this (e.g. specifying to use the github variant and setting the repo_name):
```bash
COOKIECUTTER_NO_INPUT=1 cookiecutter <raptor_repo_url> --no-input --directory package_repo additional_prompts=Github repo_name=myrepo
```
##### Prompts Explained
---

**Note:** All DevOps options have been tested using Azure DevOps, as this is the platform used by Gemeente Rotterdam which we might still have some bugs. While the GitHub workflows are included, they have not been fully tested and may contain some bugs. If you encounter any issues or have improvements, please open an issue and submit a pull request if feasible.

When you run the command, you'll see a welcome message followed by interactive prompts. These change based on whether you're using **Azure DevOps** or **GitHub**.

**Remember the following format for general parameters:**

* **DevOps**:
  `https://pkgs.dev.azure.com/<organisation_name>/<project_name>/_packaging/<package_feed>/pypi/simple/`
* **GitHub** (PyPI):
  `https://pypi.org/p/<project_name>`

---

###### 🔸 Common Prompts

| Prompt             | Description                              | Default                    |
| ------------------ | ---------------------------------------- | -------------------------- |
| Author name        | Your name                                | `"Your Name"`              |
| Author email       | Your email address                       | `"your@email.com"`         |
| Description        | Short description of the package/project | `"A short description..."` |
| Python version     | Python version to use                    | `"3.11"`                   |
| Poetry version     | Poetry tool version                      | `"2.1.3"`                  |
| Pre-commit version | Pre-commit hook version                  | `"3.4.0"`                  |

---

###### 🔹 Platform-Specific Prompts

**If `DevOps` is selected:**

| Prompt                          | Description                                                   | Default                  |
| ------------------------------- | ------------------------------------------------------------- | ------------------------ |
| DevOps Organisation name        | Your Azure DevOps organization name                           | `"organisation_name"`    |
| Project name                    | Azure DevOps project name                                     | `"project_name"`         |
| Package feed name (for pkg)     | Name of the Azure Artifacts feed (for Python packages)        | `"package_feed"`         |
| DevOps Private agent name       | The private agent for CI/CD                                   | `"private_agent_name"`   |
| Create AML environment in CI/CD | (Package repo only) Enable CI/CD support for AML environments | `False`                  |
| Azure resource group            | Resource group name                                           | `"azure_resource_group"` |
| AzureML workspace               | Workspace name                                                | `"azureml_workspace"`    |

**If `GitHub` is selected:**

| Prompt               | Description                          | Default                  |
| -------------------- | ------------------------------------ | ------------------------ |
| Azure resource group | Resource group name                  | `"azure_resource_group"` |
| AzureML workspace    | Workspace name                       | `"azureml_workspace"`    |
| Project name         | GitHub project name (used for PyPI)  | `"project_name"`         |
| Other DevOps fields  | Auto-filled with static placeholders |                          |

---

#### 3.3. Commit the template files to DevOps

Make sure to create a repo on devops or github (without readme and gitignore file) first. Then, push the local repository files by running the following from the root of the repository:
```bash
git remote add origin <repo_url>
git push -u origin --all
```
An instance may occur that your directory isn't set as a safe directory for git (usually you will get a popup for this in VS Code). If this happens, run this in the terminal:

git config --global --add safe.directory PATH/TO/REPO


#### 3.4. CI/CD

To add Continuous Integration, Continuous Delivery (CI/CD) in DevOps, go to the repository and click "set up build".

It will automatically use the azure-pipelines.yml from the root of the repository.
Click, under "run", on "save".
Now we have created a pipeline, which will be triggered when there are changes in specified folders (in principle package folder and tests folder) on specified branches (in principle main, develop and release branches).
Now we need to set branch policies (by default we only have the main and develop branch, and others need to be created). 

Navigate to branches and then set the following for the main and develop branch:
  - Require a minimum number of reviewers (2)
  - Build validation -> add build policy -> select the pipeline we just created -> save.

#TODO Github variant


#### 3.5. ML deployments (project repo)

In case of ML deployments, we also need to create an approval gate.

Approval gates are useful when deploying changes to mission-critical environents as well as enforcing good deployment practices like the 4-eyes principle for approving production deployments.
For machine learning (batch) deployments, approval gates are used to update a default batch deployment once it was successfully invoked on test data.
The update is done automatically in Azure DevOps pipeline after receiving an approval from the user who has checked that the new batch deployment was invoked successfully.

1. Create two environments in _Pipelines > Environments_: <br>
`aml_YOUR_PACKAGE_NAME_production` for main branch / production Azure ML workspace and
`aml_YOUR_PACKAGE_NAME_development` for other branches / development Azure ML workspace
2. Assign appropriate users in the corresponding environments under "Approvals and checks".
3. The pipeline YOUR_PACKAGE_NAME should get permission to access these two environments, either during the first pipeline run
or beforehand in "Environments > Environment_name > Security > Pipeline permissions".

## Environment setup

In this section, you will have setup your environment to work in and setup the dependency management properly.
Conda will setup and manage a virtual environment, with the python runtime and some base packages. Conda is also used by azureml to setup environments.
Poetry will manage all dependencies related to the python package (when using a package repo).

#### 4.1. Conda setup

If you use conda for the first time, run:
```bash
conda init
```
Close terminal and open a new one.
Then, create an environment to work in:
```bash
conda env create -n *yourenvname* -f environment.yml
conda activate *yourenvname*
```
This will create a sort of "blank" conda environment to work in. We use conda as AzureML works with conda environment.
This environment is used for local development. Subsequent installs will be done with poetry.

#### 4.2. Poetry setup

If you use poetry for the first time, do a base install of poetry by running:
```bash
curl -sSL https://install.python-poetry.org | python3 -
echo "export PATH="/home/azureuser/.local/bin:$PATH"" >> /home/azureuser/.bashrc
```
Restart terminal or open new terminal

Note that poetry can also be installed in a virtual environment using conda, so a base install of poetry is not strictly necessary. You can also do:
```bash
conda activate *environment-name*
conda install poetry
```
From there on out, the way of working remains the same

It is advised to use poetry by default to install packages.
When adding packages with poetry, the exact package information will be stored in the poetry.lock file,
which makes it easiest to reproduce the environment (compared to conda and pip as package managers).
By default, Poetry is configured to use the PyPI repository, for package installation and publishing.
Using a different (e.g. private) package repository will be covered in 4.2.2.

#### 4.2.1 Installing packages

To install the first set of packages that are added by default, go to the root directory of the repositoy, and run (from the activated environment)
```bash
poetry install
```
Note that the command above will also install the current repo code as a package. Note also that it installs packages from all dependency groups.

To add new packages using poetry, run
```bash
poetry add package_name
```
The pyproject.toml and poetry.lock files will be updated automatically.

#### 4.2.2 Installing private packages
In this section, we will explain how to use other private packages within your repository. This is very useful for re-using generic code from colleagues. 
##### 4.2.2.1 Installing private packages from artifacts feed
With the cookiecutter setup, we can install private packages from a private artifacts feed in our environment using poetry. 
This is the preferred way to use private code from other repos in our current repository. It can be used in all different CI/CD locations: locally in VS Code, remotely in the devops agent, and as a dependency in an AML environment.

**DevOps**

To install private packages in our environment, we need to be able to connect to the artifacts feed. For that, we need a personal access token (PAT) with read access to our packages.
This can be achieved by going in devops to user settings → personal access tokens → new token. Use the custom scope and check read access to Packaging.
Use the PAT to configure the following in the terminal of your compute instance

```bash
python -m keyring --disable  # keyring cannot contain duplicate keys or something, gives errors when using multiple compute instances
poetry config http-basic.private <USERNAME> <PAT>
poetry add --source private <PACKAGE_NAME>
```
This assumes the package is located in the default feed, specified in the cookiecutter prompt (TODO).

The PAT will be stored in 
```bash
/home/azureuser/.config/pypoetry/auth.toml
```
To specify a different feed, add a different source to the pyproject.toml by running
```bash
poetry source add --priority=explicit <SOURCE_NAME> <FEED_URL> (e.g. https://pkgs.dev.azure.com/ORGANISATION/PROJECT/_packaging/FEED/pypi/simple/)
```
Then the package can be added with
```bash
poetry add --source <SOURCE_NAME> <PACKAGE_NAME>
```
If the private code is still under development, it is recommended to add the repository as a submodule in the current repository. 
But instead of also installing it as an editable package to a "submodule" group with poetry, 
manually install the package from the lib/submodule location for development purposes until a registered package can be installed from the artifacts feed. 
This can also be a back and forth (e.g. first use package v1.0 install from artifacts feed, then use lib/submodule install to develop v1.1, 
then use package v1.1 from artifacts feed once v1.1 is released) if the development cycle involves both the current repository and the submodule repository. More on submodules will be explained in the section below.

NOTE: the CI/CD now makes use of a PAT to connect to the DevOps artifacts feed. However, it is still a PERSONAL access token (with read access at packaging, with limited validity), so it is dependent on one person's token being active. 
This is a workaround solution, since a functional user in devops is not always supported for every organisation.

##### 4.2.2.2 Installing private packages as custom package (from a submodule)

In case we are still developing the package dependency, we can custom install it from its repo location after cloning it as a submodules. How to initialize the git submodule in a package repo:

1. Create a `lib` folder in the root of your repo
2. Go with the terminal to this directory (`cd lib`)
3. `git submodule add git@ssh.dev.azure.com:v3/ORGANISATION/PROJECT/SUBMODULE`

By default, the default branch is tracked, but you can choose another branch in the .gitmodules file from the root of this repository. 
However, it is recommended to track the main branch, as this will ensure the module is always stable. 
You can run 'git submodule update --remote' to fetch any changes from the remote repository.
After navigating to the root of the repo for the submodule, run, with the conda environment activated,
```bash
poetry install
```
The custom package and its dependencies will be installed in editable mode (i.e. changes in the code will be live), based on its pyproject.toml.
Note that this install will not be reflected in the main package's pyproject.toml, and thus also not in its CI/CD.
If a package has private package dependencies, and these packages will be used in the CI/CD, make sure they are added to the pyproject.toml from the artifacts feed.

## Continuous Integration

In this section, we will first explain how to use pre-commit and run tests locally. Such that you can ensure that Continuous Integration (CI) pipelines will succeed. Herefater, the CI/CD workflow, security guidelines and API functionality of your new repository are elaborated on.

#### 5.1 Pre-commit
To install pre-commit into your git hooks, run from the root of your repository:
```bash
pre-commit install
```
As a check, you can run pre-commit on all files:
```bash
pre-commit run --all-files
```

The checks that are performed when running pre-commit, are defined by the pre-commit hooks in your .pre-commit-config.yaml and the rules/settings in your pyproject.toml. 
We use multiple pre-commit hooks, amongst which are:

- pre-commit (checks for merge-conflict artifacts in cod & checks yaml files, https://pre-commit.com/)
- mypy (code formatting, https://mypy-lang.org/)
- ruff (linting, amongst others, https://docs.astral.sh/ruff/rules/)
- poetry (checks package & dependency management, https://python-poetry.org/)

You can change which rules to enforce or ignore, even on a per-file or per-line basis. Do this in the pyproject.toml via the ruff rules or settings. 
There you can see the complete list of available ruff subset rules (also available at: https://docs.astral.sh/ruff/rules/).

#### 5.2 Pytest


Install packages from dependency group test (if not done already)
```bash
poetry install --only test
```
Note that packages that are needed for the unit tests need to be added to the test dependencies in poetry.
This can be done by running
```bash
poetry add package_name -G test
```
This is especially important for the CI, since only packages from the test dependency group will be installed in the environment that runs the tests!

To run the all tests, execute:
```bash
python -m pytest
```
To run only specific tests (e.g. tests in the dir unit_tests), execute:
```bash
python -m pytest tests/unit_tests
```
Using pytest-cov
To run tests with coverage, execute
```bash
python -m pytest tests/unit_tests --cov
```
Pytest-cov does not work well on Azure ML Compute Instances. It uses a sqllite3 database, which needs
to be stored. This has to be done in the ~/localfiles/ folder. Therefore, .coveragerc has a line to do
so. It stores in ~/localfiles/.coverage_{yourpackagename}. This means that you can run your tests locally
just as you would normally do.

In Pipelines, the .coverage file should be stored with default options. Therefore we added `.coveragerc_pipeline`
which configures coverage for pipelines. So if you need to tweak something regarding coverage: there is two
files you may need to deal with (`.coveragerc` for local tests and `.coveragerc_pipeline` for your pipeline).

## Writing code

#### 6.1 Using the API functionality
Our cookiecutter template is designed with simplicity and effectiveness in mind, especially for new users. It includes two key Python files: __version__.py and _api.py, each serving a distinct purpose.
The __version__.py helps with providing single-sourcing of the package version. Whereas the _api.py file acts as the primary interface for the core functionalities of the package. It is the outward-facing part of your code, meant to be used by the end-users of your package. Here's how you can use it:
The __version__.py file contains a __version__ attribute. This is useful for keeping track of the package you are working with. You can access it as follows:
```python
print(YOUR_PACKAGE_NAME.__version__)
```
The file also includes a function named multiply. This function serves as an example of how you can expose functionalities via the API. To use the multiply function:
```python
from YOUR_PACKAGE_NAME import multiply
result = multiply(2, 3)
print(result)
```

## Running code in Azure Machine Learning
TODO

## Ecosystem/resource requirements and setup
The following provides an overview of the necessary parts to make the CI/CD workflow work in either Github or DevOps, connecting with Azure Machine Learning.
A service connection from AML to a package repository is only necessary if we publish packages to a private location.
A dedicated Github/DevOps worker is only necessary if we want to work in a private environment.
Optionally, Azure Monitor Application Insights can be used to write logs to.
To use it, env variables APPLICATIONINSIGHTS_CONNECTION_STRING and APPLICATIONINSIGHTS_PROJECT_NAME should be set.
#### 8.1 DevOps
##### 8.1.1 Service connection DevOps -> AML
For performing az commands in the devops agent for AML environment creation
https://learn.microsoft.com/en-us/azure/machine-learning/how-to-setup-mlops-azureml?view=azureml-api-2&tabs=azure-shell#set-up-azure-devops
##### 8.1.2 Service connection AML -> DevOps
For building AML environments with package dependencies from the DevOps artifacts feed
Python feed connection with PAT: https://learn.microsoft.com/en-us/cli/azure/ml/connection?view=azure-cli-latest#az-ml-connection-create
PAT should be created from DevOps and have read/write scope over Packaging.
##### 8.1.3 DevOps agent
Dedicated private agent with necessary system installs (and IP whitelisting/credentials).
##### 8.1.4 Service principal for doc gen
##### 8.1.5 Library group
The template expects library groups AmlDevGroup and AmlProdGroup for connecting with Azure Machine Learning.
These library groups contain

- AML workspace credentials
- PAT for connecting from agent to artifacts feed (or use a superuser)
- Keyvault name and keys for doc publication on DevOps Wiki

In it, we need at least the following keys:
For connecting with Azure Machine Learning:
AmlServiceConnection
AmlWorkspaceName
AmlResourceGroup

For connecting with the DevOps artifacts feed: 
PatUsername
DevOpsPAT

For connecting with the DevOps Wiki (and getting credentials from a shared keyvault):
SharedKeyvault
TenantName

And optionally, for connecting with a keyvault (see also use_keyvault_template.yml in the project repo):
AmlServiceConnection
AmlKeyvaultName
AmlPatSecretName

##### 8.1.6 Keyvault
Necessary for Service principal for wiki generation (todo: change to service connection).
We need to have keys SP-Wiki-ID and SP-Wiki-SECRET stored in our keyvault in order to publish the docs to our DevOps Wiki.

#### 8.1 Github
Doc generation is not implemented yet.
##### 8.1.1 Service principal Github -> AML
Set up Azure Login action with the Service Principal secret in GitHub Actions workflows
https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-secret
##### 8.1.2 Using Github secrets
https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions#using-secrets-in-a-workflow

## Resources

* [Releases](changelog.md)

## Known Issues

* If you choose the GitHub platform, components will not work since we haven't fixed the --extra-index-url parameter inside the env.yml files. We will fix this at a later stage.

* If you choose the GitHub platform, the doc generation will not work, but you can run it locally with the Sphinx command.

**Note:** All DevOps options have been tested using Azure DevOps, as this is the platform used by Gemeente Rotterdam which we might still have some bugs. While the GitHub workflows are included, they have not been fully tested and may contain some bugs. If you encounter any issues or have improvements, please open an issue and submit a pull request if feasible.

## License

This project is licensed under the **European Union Public Licence (EUPL) v1.2**.  
For more details, see the [EUPL official website](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12).