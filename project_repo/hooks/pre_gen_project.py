"""
# We use a docstring here so that we have a valid Python file that allows us to access the Jinja2 templating engine

    {% set is_devops = cookiecutter.additional_prompts.lower() == "devops" %}
    {% set is_github = cookiecutter.additional_prompts.lower() == "github" %}

    {# DevOps-specific prompt #}
    {% if is_devops %}
        {{ cookiecutter.update({"organisation_name": prompt_user("DevOps Organisation name", "organisation_name")}) }}
        {{ cookiecutter.update({"private_agent_name": prompt_user("DevOps Private agent name", "private_agent_name")}) }}
        {{ cookiecutter.update({"azure_resource_group": "azure_resource_group"}) }}
        {{ cookiecutter.update({"azureml_workspace": "azureml_workspace"}) }}
    {% endif %}

    {# GitHub-specific prompts #}
    {% if is_github %}
        {{ cookiecutter.update({"azure_resource_group": prompt_user("Azure resource group", "azure_resource_group")}) }}
        {{ cookiecutter.update({"azureml_workspace": prompt_user("AzureML workspace", "azureml_workspace")}) }}
        {{ cookiecutter.update({"organisation_name": "organisation_name"}) }}
        {{ cookiecutter.update({"private_agent_name": "private_agent_name"}) }}
    {% endif %}

"""

# ruff: noqa: INP001, S603, S607, T201

import re
import subprocess
import sys

subprocess.call(["git", "config", "--global", "init.defaultBranch", "main"])


MODULE_REGEX = r"^[a-zA-Z]([-a-zA-Z0-9]*[a-zA-Z0-9])?$"

aml_base_deployment_name = (
    "{{ cookiecutter.repo_name.lower().replace(' ', '-').replace('_', '-') }}"
)
aml_base_deployment_name = (
    "{{ cookiecutter.repo_name.lower().replace(' ', '-').replace('_', '-') }}"
)
min_char_number = 3
max_char_number = 20

if not re.match(MODULE_REGEX, aml_base_deployment_name):
    print(
        f"ERROR: AML endpoint / deployment base name '{aml_base_deployment_name}' should only consist of letters, "
        "dashes and numbers and must begin with a letter."
    )
    sys.exit(1)
if (
    len(aml_base_deployment_name) < min_char_number
    or len(aml_base_deployment_name) > max_char_number
):
    print(
        f"ERROR: AML endpoint / deployment base name '{aml_base_deployment_name}' should be "
        f"{min_char_number}-{max_char_number} characters in length."
    )
    sys.exit(1)
