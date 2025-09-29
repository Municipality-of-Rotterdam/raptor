import pytest
from {{ cookiecutter.repo_name }}.examples import ModuloChecker, BitwiseChecker, LastCharacterChecker


@pytest.fixture(params=[
    pytest.param(ModuloChecker(), id="modulo"),
    pytest.param(BitwiseChecker(), id="bitwise"),
    pytest.param(LastCharacterChecker(), id="lastchar"),
])
def isodd_strategy(request):
    """
    Fixture that returns all local OddChecker implementations (RemoteChecker connects
    to an external API)
    """
    return request.param
