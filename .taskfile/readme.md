# Taskfile

This is a taskfile containing a collection of commands for various tasks, such as:

- Setting up a new compute instance
- Creating a new repository based on cookiecutter
- Setting up a repository for use (including setting up the python environment)

Compared to following the confluence documentation, this taskfile will automates as many tasks as possible.
Additionally, for some, by going through all tasks step-by-step makes it easier to follow everything and not forget something.

Important: the taskfiles are developed and tested on Ubuntu. For other linux distributions you might need small changes (related to apt-get/snap installations or paths).

## Installation

Install taskfile, on Ubuntu: `sudo snap install task --classic`. See https://taskfile.dev/docs/installation for other methods.

### Config

To fully configure taskfile, create both files as explained below.

#### Taskfile config

To configure taskfile itself, create a .taskrc.yml in your home folder, for example with `nano ~/.taskrc.yml`. Below an example:

```
interactive: true  # get prompts for missing variables instead of errors
experiments:
  REMOTE_TASKFILES: 1  # enable remote taskfiles
remote:
  cache-dir: ~/.task  # store cache in home folder, not within git repos
  trusted-hosts:
    - github.com  # disable prompts when downloading remote taskfiles from github, remove setting for extra security
```

#### Environment variables

To set some default values to be used in the tasks from this repo, create a taskfile.env file in your home folder, for example with `nano ~/taskfile.env`.

For now the following variables can be set:

- COOKIECUTTER_URL: the url pointing to the cookiecutter url (defaults to [raptor](https://github.com/Municipality-of-Rotterdam/raptor)).
- COOKIECUTTER_CONFIG: url pointing to cookiecutter config instructions (defaults to [raptor](https://github.com/Municipality-of-Rotterdam/raptor) readme).
- GIT_ROOT_HTTPS: url to git provider, with organisation/project names, without trailing slash. Example: https://dev.azure.com/ORGANISATION/PROJECT.
- GIT_ROOT: base https/ssh url without trailing slash. Example: git@ssh.dev.azure.com:v3/ORGANISATION/PROJECT.
- GIT_PUBLIC_KEY_URL: url on git provider to add public keys. Example: https://dev.azure.com/ORGANISATION/_usersSettings/keys.

Only GIT_ROOT is required, the others have defaults (but some steps might be skipped).

Full example:

```
COOKIECUTTER_URL=https://github.com/Municipality-of-Rotterdam/raptor  # link to cookiecutter repo
COOKIECUTTER_CONFIG=https://github.com/Municipality-of-Rotterdam/raptor  # link to cookiecutter config file for your team
GIT_ROOT_HTTPS=https://dev.azure.com/ORGANISATION/PROJECT  # git root https url (including organisation/project)
GIT_ROOT=git@ssh.dev.azure.com:v3/ORGANISATION/PROJECT  # git root ssh url (including organisation/project), without trailing slash
GIT_PUBLIC_KEY_URL=https://dev.azure.com/ORGANISATION/_usersSettings/keys  # git https url to page for adding new public keys
```

## Running tasks

You can run a task with `task --taskfile https://github.com/Municipality-of-Rotterdam/raptor.git//.taskfile/taskfile.yml?ref=develop TASK_NAME`.

In `taskfile.yml` you can find most important task and 'main' tasks calling subtasks.
Those subtasks are located in separate taskfiles in the `tasks` directory, loosely structured per theme.
You can call a subtask directly by refering to `FOLDER_NAME:SUBTASK_NAME` if necessary.

You can add arguments to a task by appending `KEY=VALUE` to the command. Below only the important arguments are showed, see the taskfiles for more information.

### setup_compute_instance

Setting up a new compute instance. Setting up ssh key to connect with git, setting code tunnel, installing poetry, uv, etc.

#### setup_compute_instance:reinstall_code_tunnel_service

When code tunnel service doesn't work anymore (login token expired)

### create_new_repo

Create new git repo based on raptor.
Should be run in the directory in which you want to create a folder containing the repo.

Arguments:
- PKG_NAME: name of the python package (containing letters, numbers and underscores)
- REPO_TYPE: package_repo (default), project_repo
- GIT_ROOT: base https/ssh url without trailing slash. Example: git@ssh.dev.azure.com:v3/ORGANISATION/PROJECT.

### setup_repo

Setup the current git repo: creating python environment, installing precommit, etc.
Should be run in the repo itself using the following:

1. When using an older raptor-based repo based on poetry, copy https://github.com/Municipality-of-Rotterdam/raptor/blob/develop/package_repo/%7B%7B%20cookiecutter.repo_name%20%7D%7D/taskfile.yml into your repo.
2. Open the taskfile.yml in the repo and check all vars values!
3. Then run 'task setup_repo' in your terminal, while in your repo directory.

Arguments:
- REPO_TYPE: package_repo (default), project_repo

## Resources

* [Taskfile website](https://taskfile.dev)
* [Documentation remote taskfiles](https://taskfile.dev/docs/experiments/remote-taskfiles)
 