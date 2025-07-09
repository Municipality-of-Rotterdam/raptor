import os
from cookiecutter.prompt import read_user_variable, read_user_yes_no, read_user_choice  # type: ignore
from jinja2.ext import Extension  # type: ignore

# Detect non-interactive mode via env var
NO_INPUT = os.environ.get("COOKIECUTTER_NO_INPUT", "0") == "1"

# Default values for non-interactive mode
DEFAULT_VALUES = {
    "organisation_name": "default_organisation",
    "project_name": "default_project",
    "repo_name": "default_repo",
    "python_version": "3.11",
    "poetry_version": "2.1.3",
    "precommit_version": "3.4.0",
    "type_deployment": "none",
}

# Prompts to display in interactive mode
ADDITIONAL_PROMPTS = {
    "organisation_name": "DevOps organisation name",
    "project_name": "The project name",
    "repo_name": "Enter a repository name",
    "python_version": "Python version",
    "poetry_version": "Poetry version",
    "precommit_version": "Pre-commit version",
    "type_deployment": "Select the type of deployment",
}


class AdditionalPrompts(Extension):
    def __init__(self, environment):
        """Jinja2 Extension Constructor."""
        super().__init__(environment)

        def prompt_user(var_name, default=None):
            if NO_INPUT:
                return DEFAULT_VALUES.get(var_name, default)
            return read_user_variable(var_name, default, prompts=ADDITIONAL_PROMPTS)

        def prompt_user_choices(var_name, choices):
            if NO_INPUT:
                return DEFAULT_VALUES.get(var_name, choices[0])
            return read_user_choice(var_name, options=choices, prompts=ADDITIONAL_PROMPTS)

        def prompt_user_yes_no(var_name, default=True):
            if NO_INPUT:
                return DEFAULT_VALUES.get(var_name, default)
            return read_user_yes_no(var_name, default, prompts=ADDITIONAL_PROMPTS)

        environment.globals.update(
            prompt_user=prompt_user,
            prompt_user_choices=prompt_user_choices,
            prompt_user_yes_no=prompt_user_yes_no,
        )
