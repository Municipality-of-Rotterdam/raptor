"""This file contains example unit tests. 
A unit test is a test of a smallest unit of work. For example, one function.
Make sure that all unit tests are light-weight.
Make sure that all unit tests assert that the outcome of a function is as expected.
Do not make connections to databases or any outside sources (ie networking components)."""

import pytest
from {{ cookiecutter.package_name }}.examples import multiply, divide

def test_multiply():
    assert multiply(2.0, 3.0) == 6.0
    assert multiply(-2.0, 3.0) == -6.0
    assert multiply(0.0, 5.0) == 0.0
    assert multiply(2.5, 4.0) == 10.0
    assert multiply(-1.5, -2.0) == 3.0

def test_divide():
    assert divide(6.0, 3.0) == 2.0
    assert divide(-6.0, 3.0) == -2.0
    assert divide(7.5, 2.5) == 3.0
    assert divide(-9.0, -3.0) == 3.0
    
    with pytest.raises(ZeroDivisionError):
        divide(5.0, 0.0)
