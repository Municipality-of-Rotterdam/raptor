import urllib.request
import json
import pathlib
from abc import ABC, abstractmethod

"""
4 different strategies to check for odd numbers and some functions that extend on 
that ability.

This is just to demonstrate some testing concepts and pytest features. In general, 
do not bother testing functionality if it boils down to Python's own stdlib
or (mature) external packages as both are thoroughly tested. 
"""


class OddChecker(ABC):
    def is_odd(self, number: int) -> bool:
        if type(number) is not int:
            raise TypeError(f"is_odd expects int, not {type(number)}")
        return self._check(number)

    @abstractmethod
    def _check(self, number: int) -> bool:
        pass


class ModuloChecker(OddChecker):
    def _check(self, number: int) -> bool:
        return number % 2 == 1


class BitwiseChecker(OddChecker):
    def _check(self, number: int) -> bool:
        return number & 1 == 1


class LastCharacterChecker(OddChecker):
    def _check(self, number: int) -> bool:
        return str(abs(number))[-1] in "13579"


class RemoteChecker(OddChecker):
    def _check(self, number: int) -> bool:
        url = f"https://api.isevenapi.xyz/api/iseven/{number}/"
        response = urllib.request.urlopen(url)
        raw_data = response.read()
        data = json.loads(raw_data)
        return not data["iseven"]


def count_odds(numbers: list[int], strategy: OddChecker) -> int:
    return len([n for n in numbers if strategy.is_odd(n)])


def count_odds_to_file(
    numbers: list[int], filepath: pathlib.Path, strategy: OddChecker
) -> None:
    n_odd_numbers = count_odds(numbers, strategy=strategy)
    with open(filepath, "w") as f:
        f.write(f"{n_odd_numbers}\n")
