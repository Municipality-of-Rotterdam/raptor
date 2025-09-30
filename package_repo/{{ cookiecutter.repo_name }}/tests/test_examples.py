import pytest
from math import pi
from io import BytesIO
import json
from urllib.error import HTTPError
from {{ cookiecutter.package_name }}.examples import count_odds, count_odds_to_file, RemoteChecker

"""
The fixtures are imported implicitely, you can find them at tests/conftest.py
"""

@pytest.mark.parametrize("number, odd_bool", [(0, False), (-1, True), (1, True), (2, False)])
@pytest.mark.example
def test_is_odd_valid(isodd_strategy, number, odd_bool):
    """
    Demonstrates how fixtures and parameterization can be used to quickly generate a large
    number of test conditions (12 in this case: 3 strategies and 4 params)
    """
    assert isodd_strategy.is_odd(number) == odd_bool

@pytest.mark.parametrize("number", [1.0, 1.1, "een", float("inf"), pi])
@pytest.mark.example
def test_is_odd_invalid(isodd_strategy, number):
    """
    Demonstrates how testing for exceptions can communicate developer intent (i.e. you 
    show that you wanted to raise this specific exception under these specific conditions)
    """
    with pytest.raises(TypeError):
        isodd_strategy.is_odd(number)
  
@pytest.mark.parametrize("number, odd_bool", [(0, False), (-1, True), (1, True), (2, False)])
@pytest.mark.example
def test_remote_checker_valid(mocker, number, odd_bool):
    """
    Demonstrates how you can mock parts you'd rather not run constantly (expensive, slow,
    unreliable, unavailable or external parts), while still testing the parts that rely
    on them.
    """
    filelike_response = BytesIO(json.dumps({"iseven": not odd_bool}).encode("utf-8"))
    mocker.patch("urllib.request.urlopen", return_value = filelike_response)
    assert RemoteChecker().is_odd(number) == odd_bool
        
@pytest.mark.parametrize("number", [1.0, 1.1, "een", float("inf"), pi])
@pytest.mark.example
def test_remote_checker_invalid(mocker, number):
    """
    Demonstrates that the parts you choose to mock matters as you essentially have to
    simulate them (including their own error conditions)
    """
    http_error = HTTPError(
        url=f"https://api.isevenapi.xyz/api/iseven/{number}/",
        code=400,
        msg="BAD REQUEST",
        hdrs=None,
        fp=None
    )
    mocker.patch("urllib.request.urlopen", side_effect = http_error)
    with pytest.raises(HTTPError):
        RemoteChecker()._check(number)

@pytest.mark.parametrize("numbers, n_odds", [((2, 3, 4), 1), ((-1, -2, -3), 2)])
@pytest.mark.example
def test_count_odds_to_file(tmp_path, isodd_strategy, numbers, n_odds):
    """
    Demonstrates how the implicit tmp_path fixture can provide a place to read from or 
    write to (scoped per test by default; deleted over time, see 
    https://docs.pytest.org/en/stable/how-to/tmp_path.html#temporary-directory-location-and-retention
    for the specifics).

    Useful if your functions output files that you want to check and/or if said output
    is needed as input (although you'd generally want to use fixtures for this).
    """
    text_path = tmp_path / "odd_numbers.txt"
    count_odds_to_file(numbers, text_path, isodd_strategy)
    assert int(text_path.read_text()) == n_odds

@pytest.mark.parametrize("numbers, odd_bools, n_odds", [((0, 1, 2, 3, 4), (False, True, False, True, False), 2)])
@pytest.mark.example
def test_count_odds_isolated(mocker, numbers, odd_bools, n_odds):
    """
    Demonstrates how mocking can be used to test functionality in isolation. In this case, count_odds
    in isolation of a specific OddChecker implementation.
    """
    fake_strategy = mocker.Mock()
    fake_strategy.is_odd.side_effect = odd_bools
    assert count_odds(numbers, fake_strategy) == n_odds
