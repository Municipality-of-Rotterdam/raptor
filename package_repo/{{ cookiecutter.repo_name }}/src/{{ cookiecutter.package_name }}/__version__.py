# mypy: ignore-errors
"""Module for retrieving and handling the version information of the package."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    # Python 3.8 and above
    from importlib.metadata import version as ilib_version
except ImportError:
    # Python 3.7 compatibility (requires `importlib_metadata` to be installed; TODO consider dropping support entirely)
    from importlib_metadata import version as ilib_version


if TYPE_CHECKING:
    from collections.abc import Callable

# The metadata.version that we import for Python 3.7 is untyped, work around
# that.
version: Callable[[str], str] = ilib_version

__version__ = version("{{cookiecutter.package_name }}")
