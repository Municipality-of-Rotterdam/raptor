import os
from cookiecutter.prompt import read_user_variable, read_user_yes_no, read_user_choice  # type: ignore
from jinja2.ext import Extension  # type: ignore

# Default values for non-interactive mode
DEFAULT_VALUES = {
    "azure_resource_group": "default_resource_group",
    "azureml_workspace": "default_workspace",
    "organisation_name": "organisation_name",
    "package_feed": "package_feed",
    "create_aml_environment_in_cicd": "n",
    "author_name": "Your Name",
    "author_email": "your@email.com",
    "description": "A short description of the package.",
    "python_version": "3.11",
    "poetry_version": "2.1.3",
    "precommit_version": "3.4.0",
}

# Detect if we are in non-interactive mode
NO_INPUT = os.environ.get("COOKIECUTTER_NO_INPUT", "0") == "1"

class AdditionalPrompts(Extension):
    def __init__(self, environment):
        super().__init__(environment)

        def prompt_user(var_name, default=None):
            if NO_INPUT:
                return DEFAULT_VALUES.get(var_name, default)
            return read_user_variable(var_name, default)

        def prompt_user_choices(var_name, choices):
            if NO_INPUT:
                return DEFAULT_VALUES.get(var_name, choices[0])
            return read_user_choice(var_name, options=choices)

        def prompt_user_yes_no(var_name, default=True):
            if NO_INPUT:
                return DEFAULT_VALUES.get(var_name, default)
            return read_user_yes_no(var_name, default)

        environment.globals.update(
            prompt_user=prompt_user,
            prompt_user_choices=prompt_user_choices,
            prompt_user_yes_no=prompt_user_yes_no,
        )
