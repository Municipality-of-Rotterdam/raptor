"""
# We use a docstring here so that we have a valid Python file that allows us to access the Jinja2 templating engine

    {% set is_devops = cookiecutter.additional_prompts.lower() == "devops" %}
    {% set is_github = cookiecutter.additional_prompts.lower() == "github" %}

    {# Common prompts #}
    {{ cookiecutter.update({"author_name": prompt_user("Author name", "Your Name")}) }}
    {{ cookiecutter.update({"author_email": prompt_user("Author email", "your@email.com")}) }}
    {{ cookiecutter.update({"description": prompt_user("Description", "A short description of the package.")}) }}
    {{ cookiecutter.update({"python_version": prompt_user("Python version", "3.11")}) }}
    {{ cookiecutter.update({"poetry_version": prompt_user("Poetry version", "2.1.3")}) }}
    {{ cookiecutter.update({"precommit_version": prompt_user("Pre-commit version", "3.4.0")}) }}

    {# DevOps-specific prompt #}
    {% if is_devops %}
        {{ cookiecutter.update({"organisation_name": prompt_user("organisation_name")}) }}
        {{ cookiecutter.update({"package_feed": prompt_user("package_feed")}) }}
        {{ cookiecutter.update({"create_aml_environment_in_cicd": prompt_user_yes_no("create_aml_environment_in_cicd", False)}) }}
        {{ cookiecutter.update({"private_agent_name": prompt_user("private_agent_name")}) }}
        {{ cookiecutter.update({"azure_resource_group": "azure_resource_group"}) }}
        {{ cookiecutter.update({"azureml_workspace": "azureml_workspace"}) }}
    {% endif %}

    {# GitHub-specific prompts #}
    {% if is_github %}
        {{ cookiecutter.update({"azure_resource_group": prompt_user("azure_resource_group")}) }}
        {{ cookiecutter.update({"azureml_workspace": prompt_user("azureml_workspace")}) }}
        {{ cookiecutter.update({"organisation_name": "organisation_name"}) }}
        {{ cookiecutter.update({"create_aml_environment_in_cicd": prompt_user_yes_no("create_aml_environment_in_cicd", False)}) }}
        {{ cookiecutter.update({"package_feed": "package_feed"}) }}
        {{ cookiecutter.update({"private_agent_name": "private_agent_name"}) }}
    {% endif %}
"""

# ruff: noqa: INP001, S603, S607

import subprocess
import re
import sys

subprocess.call(["git", "config", "--global", "init.defaultBranch", "main"])

AUTHORREGEX = r"([A-Za-z]+ )+[A-Za-z]+$"  # matches also spaces between name surname and tussenvoegsels
EMAILREGEX = r"[A-Za-z0-9._]+@[A-Za-z0-9_].+[A-Za-z]+$"  # matches alphanumeric.withoptionaldot@alphanumeric.letters
PACKAGE_NAME_REGEX = r"^[a-zA-Z0-9_]+$"  # matches alphanumeric or underscores

author_name = "{{ cookiecutter.author_name}}"
author_email = "{{ cookiecutter.author_email}}"
package_name = "{{ cookiecutter.package_name }}"

if not re.match(PACKAGE_NAME_REGEX, package_name):
    print(
        f"ERROR: package name '{package_name}' is not valid. It should contain only alphanumeric characters and underscores."
    )
    sys.exit(1)

if not re.match(AUTHORREGEX, author_name):
    print(
        f"ERROR: author name '{author_name}' is not valid. Should be like: Name [tussenvoegsel] Surname"
    )
    sys.exit(1)
if not re.match(EMAILREGEX, author_email):
    print(
        f"ERROR: author email '{author_email}' is not valid. Should be like: nameornumber.nameornumber@my.domain"
    )
    sys.exit(1)
