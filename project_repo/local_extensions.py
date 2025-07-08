from cookiecutter.prompt import read_user_variable, read_user_yes_no, read_user_choice  # type: ignore
from jinja2.ext import Extension  # type: ignore

ADDITIONAL_PROMPTS = {
    "organisation_name": "organisation_name",
}


class AdditionalPrompts(Extension):
    def __init__(self, environment):
        """Jinja2 Extension Constructor."""
        super().__init__(environment)

        def prompt_user(var_name, default=None):
            return read_user_variable(var_name, default, prompts=ADDITIONAL_PROMPTS)

        def prompt_user_choices(var_name, choices):
            return read_user_choice(
                var_name, options=choices, prompts=ADDITIONAL_PROMPTS
            )

        def prompt_user_yes_no(var_name, default=True):
            return read_user_yes_no(var_name, default, prompts=ADDITIONAL_PROMPTS)

        # Make these functions available to the Jinja2 context
        environment.globals.update(
            prompt_user=prompt_user,
            prompt_user_choices=prompt_user_choices,
            prompt_user_yes_no=prompt_user_yes_no,
        )
