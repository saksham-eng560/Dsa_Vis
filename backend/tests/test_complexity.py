"""Static Big-O heuristics on classic algorithms (Python + C-family)."""

import ast

import pytest

from core.c_complexity_facts import c_facts
from core.complexity_analyzer import estimate
from core.complexity_facts import python_facts
from tests.samples import C_CASES, CASES


@pytest.mark.parametrize("name", CASES)
def test_python_cases(name: str) -> None:
    code, best, worst, space = CASES[name]
    result = estimate(python_facts(ast.parse(code)))
    assert (result.time.best, result.time.worst, result.space.complexity) == (best, worst, space)
    assert result.time.explanation


@pytest.mark.parametrize("name", C_CASES)
def test_c_cases(name: str) -> None:
    code, worst = C_CASES[name]
    assert estimate(c_facts(code)).time.worst == worst


def test_quicksort_average_differs_from_worst() -> None:
    code = CASES["quick"][0]
    result = estimate(python_facts(ast.parse(code)))
    assert result.time.average == "O(n log n)"
