"""Check that raptor_template_version in copier.yaml equals the version in pyproject.toml.

The generated repos refer to the raptor repo by this version (git tag), so both must be bumped together.
Only uses the standard library, needs python >= 3.11 (tomllib). The pre-commit hook runs it with uv.
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# the 'default' of the raptor_template_version question in copier.yaml
# (a regex, as PyYAML is not installed when the hook runs with uv run --no-sync)
COPIER_VERSION_PATTERN = re.compile(
    r"^raptor_template_version:[ \t]*\n(?:[ \t]+.*\n|[ \t]*\n)*?[ \t]+default:[ \t]*[\"']?([^\"'\s#]+)",
    re.MULTILINE,
)


def main() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    pyproject_version = pyproject["project"]["version"]

    copier_match = COPIER_VERSION_PATTERN.search((ROOT / "copier.yaml").read_text())
    if copier_match is None:
        print(
            "ERROR: could not find the default of raptor_template_version in copier.yaml"
        )
        return 1
    copier_version = copier_match.group(1)

    if copier_version != pyproject_version:
        print(
            f"ERROR: raptor_template_version in copier.yaml is '{copier_version}', "
            f"but the version in pyproject.toml is '{pyproject_version}'. Bump both together."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
