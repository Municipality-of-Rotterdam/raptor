"""
This module defines a Jinja2 extension that adds custom prompting behavior for Cookiecutter templates.
It supports:
- Loading default context values from a config file (via COOKIECUTTER_CONFIG environment variable, 
    make sure to run export COOKIECUTTER_CONFIG=path_to_config.yml)
- Using default values in non-interactive mode (--no-input)
- Human-friendly prompt labels
"""

import os
import yaml
from pathlib import Path
from cookiecutter.prompt import read_user_variable, read_user_yes_no, read_user_choice
from jinja2.ext import Extension  # type: ignore

# Detect non-interactive mode
NO_INPUT = os.environ.get("COOKIECUTTER_NO_INPUT", "0") == "1"

# Load default context from config file (if specified)
CONFIG_PATH = os.environ.get("COOKIECUTTER_CONFIG")
DEFAULT_CONTEXT_FROM_FILE = {}

if CONFIG_PATH and Path(CONFIG_PATH).exists():
    with open(CONFIG_PATH, "r") as f:
        loaded = yaml.safe_load(f)
        DEFAULT_CONTEXT_FROM_FILE = loaded.get("default_context", {})

def get_context_value(var_name: str, fallback=None):
    """
    Return the value for a variable from the loaded config file, or fallback if not found.
    
    Parameters:
    -----------
    var_name : str
        The name of the variable to retrieve.
    fallback : any
        A default fallback value if the variable is not found.
    
    Returns:
    --------
    any
        The resolved value.
    """
    if var_name in DEFAULT_CONTEXT_FROM_FILE:
        return DEFAULT_CONTEXT_FROM_FILE[var_name]

    return fallback

# Default values for non-interactive mode
DEFAULT_VALUES = {
    "azure_resource_group": "default_resource_group",
    "azureml_workspace": "default_workspace",
    "organisation_name": "organisation_name",
    "package_feed": "package_feed",
    "github_service_connection": "github-ci-templates",
    "private_agent_name": "private_agent_name",
    "publish_package_on_public_pypi": "y",
    "create_aml_environment_in_cicd": "y",
    "author_name": "Your Name",
    "author_email": "your@email.com",
    "description": "A short description of the package.",
    "python_version": "3.11",
    "uv_version": "0.10.6",
    "precommit_version": "3.4.0",
}

# Prompt labels
ADDITIONAL_PROMPTS = {
    "organisation_name": "DevOps Organisation name",
    "package_feed": "Package feed name",
    "github_service_connection": "The DevOps service connection required to connect to github",
    "private_agent_name": "DevOps Private agent name",
    "author_name": "Author name",
    "author_email": "Author email",
    "description": "Description",
    "python_version": "Python version",
    "uv_version": "uv version",
    "precommit_version": "Pre-commit version",
}

class AdditionalPrompts(Extension):
    """
    Jinja2 extension to support enhanced user prompting in Cookiecutter templates.
    
    Adds global functions:
        - prompt_user
        - prompt_user_choices
        - prompt_user_yes_no
    
    These functions will:
    - Respect COOKIECUTTER_NO_INPUT for non-interactive runs
    - Use values from COOKIECUTTER_CONFIG if present
    - Otherwise, fall back to DEFAULT_VALUES or interactive prompts
    """
    def __init__(self, environment):
        super().__init__(environment)

        def prompt_user(var_name: str, default=None):
            """
            Prompt the user for a string variable, or use defaults/config.

            Parameters:
            -----------
            var_name : str
                The name of the variable (used as key).
            default : any
                Default fallback value.

            Returns:
            --------
            str
                Final value for the variable.
            """
            default_value = get_context_value(var_name, DEFAULT_VALUES.get(var_name, default))
            if NO_INPUT:
                return default_value
            return read_user_variable(var_name, default_value, prompts=ADDITIONAL_PROMPTS)

        def prompt_user_choices(var_name: str, choices):
            """
            Prompt the user to choose from a list of options.

            Parameters:
            -----------
            var_name : str
                The name of the variable.
            choices : list
                The list of available options.

            Returns:
            --------
            str
                The chosen option.
            """
            default_value = get_context_value(var_name, DEFAULT_VALUES.get(var_name, choices[0]))
            if NO_INPUT:
                return default_value
            return read_user_choice(var_name, options=choices, prompts=ADDITIONAL_PROMPTS)

        def prompt_user_yes_no(var_name: str, default=True):
            """
            Prompt the user for a yes/no question.

            Parameters:
            -----------
            var_name : str
                The name of the variable.
            default : bool
                The default value if not provided.

            Returns:
            --------
            bool
                User selection as boolean.
            """
            default_value = get_context_value(var_name, DEFAULT_VALUES.get(var_name, default))
            if NO_INPUT:
                return default_value
            return read_user_yes_no(var_name, default_value, prompts=ADDITIONAL_PROMPTS)

        environment.globals.update(
            prompt_user=prompt_user,
            prompt_user_choices=prompt_user_choices,
            prompt_user_yes_no=prompt_user_yes_no,
        )
