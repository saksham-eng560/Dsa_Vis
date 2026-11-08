import pytest

from api.schemas.response import AnalysisResult, Complexity, TimeComplexity
from core.llm_merge import merge_analysis, normalize_big_o


@pytest.mark.parametrize("raw,expected", [
    ("O(n^2)", "O(n²)"), ("O(n**3)", "O(n³)"), ("O(2^n)", "O(2ⁿ)"),
    ("O(nlogn)", "O(n log n)"), ("O(n * log(n))", "O(n log n)"), ("O(log(n))", "O(log n)"), ("O(1)", "O(1)"),
])
def test_normalize_big_o(raw: str, expected: str) -> None:
    assert normalize_big_o(raw) == expected


def test_equivalent_notation_does_not_warn() -> None:
    static = AnalysisResult(language="python", complexity=Complexity(
        time=TimeComplexity(best="O(n)", average="O(n²)", worst="O(n²)"), source="static"))
    llm = {"complexity": {"time": {"best": "O(n)", "average": "O(n^2)", "worst": "O(n^2)", "explanation": "x"},
                          "space": {"complexity": "O(1)", "explanation": "y"}}}
    merged = merge_analysis(static, llm)
    assert merged.complexity.time.worst == "O(n²)" and not merged.warnings


def test_bad_complexity_keeps_static() -> None:
    static = AnalysisResult(language="python", complexity=Complexity(source="static"))
    merged = merge_analysis(static, {"complexity": {"time": {"worst": "quadratic"}}})
    assert merged.complexity.source == "static"
