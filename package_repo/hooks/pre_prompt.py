import tomllib
import pathlib
import json

raptor_root = pathlib.Path(__file__).parents[2]
repo_root = pathlib.Path(__file__).parents[1]
toml_path = raptor_root / "pyproject.toml"
cookiecutter_config_path = repo_root / "cookiecutter.json"

# reading raptor version
raptor_config = tomllib.load(open(toml_path, "rb"))
raptor_version = raptor_config["project"]["version"]

# setting template version and dumping it back to JSON
cookiecutter_config = json.loads(cookiecutter_config_path.read_text())
cookiecutter_config["__cookiecutter_template_version"] = raptor_version
cookiecutter_config_path.write_text(json.dumps(cookiecutter_config, indent=4))
