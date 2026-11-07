"""Flowcharts must be well-formed graphs with sensible structure."""

import ast

import pytest

from api.schemas.response import Flowchart
from core.c_flowchart import c_flowchart
from core.diagram_generator import python_flowchart

PY = """def search(arr, t):
    for i, x in enumerate(arr):
        if x == t:
            return i
    return -1

def loop(n):
    total = 0
    while n > 0:
        if n % 2:
            n -= 1
            continue
        n //= 2
    print(total)

print(search([1, 2], 2))
"""

CPP = """#include <iostream>
int find(int a[], int n, int t) {
    for (int i = 0; i < n; i++) {
        if (a[i] == t) return i;
        else continue;
    }
    return -1;
}
int main() { std::cout << find(nullptr, 0, 1); return 0; }
"""

GO = """package main
func sum(xs []int) int {
    s := 0
    for _, x := range xs {
        if x < 0 {
            break
        }
        s += x
    }
    return s
}
"""


def assert_well_formed(chart: Flowchart) -> None:
    ids = {n.id for n in chart.nodes}
    assert len(ids) == len(chart.nodes)
    for e in chart.edges:
        assert e.source in ids and e.target in ids
    for group in {n.group for n in chart.nodes}:
        kinds = [n.type for n in chart.nodes if n.group == group]
        assert kinds.count("start") == 1 and "end" in kinds


def test_python_groups_and_branches() -> None:
    chart = python_flowchart(ast.parse(PY), PY)
    assert_well_formed(chart)
    assert {n.group for n in chart.nodes} == {"search", "loop", "<program>"}
    decisions = [n for n in chart.nodes if n.type == "decision"]
    assert any(n.label.startswith("for i, x in") for n in decisions)
    labels = {e.label for e in chart.edges}
    assert {"True", "False", "next", "done", "continue"} <= labels
    returns = [n for n in chart.nodes if n.label.startswith("return")]
    assert all(n.line for n in returns)


@pytest.mark.parametrize("code,group", [(CPP, "find"), (GO, "sum")])
def test_c_family(code: str, group: str) -> None:
    chart = c_flowchart(code)
    assert_well_formed(chart)
    assert group in {n.group for n in chart.nodes}
    assert any(n.type == "decision" for n in chart.nodes if n.group == group)


def test_c_family_garbage_does_not_crash() -> None:
    assert_well_formed(c_flowchart("}}} {{{ ;;; if ( while"))
