"""Extract `FuncFacts` from C-family structural IR (see `c_parser.py`)."""

import re

from core.c_parser import CParser, Stmt
from core.complexity_analyzer import LOG, NLOGN, ONE, Cost, FuncFacts, N
from core.complexity_facts import HALVING_RX, MEMO_RX, shrink_kind

_C_ALLOC_RX = re.compile(r"\bnew\s+\w+\[|vec!|make\(|new (ArrayList|HashMap|HashSet)|vector<|\[\]\s*=|\.push|\.append")

def c_facts(code: str) -> list[FuncFacts]:
    stmts = CParser(code).parse()
    funcs = [s for s in stmts if s.kind == "func"]
    funcs += [f for s in stmts if s.kind == "block" for f in s.body if f.kind == "func"]
    facts = [_c_function(f) for f in funcs]
    known = {f.name for f in funcs}
    for fact, fn in zip(facts, funcs):
        text = _flat_text(fn.body)
        fact.callees = [(name, ONE) for name in known - {fn.name} if re.search(rf"\b{name}\s*\(", text)]
    return facts


def _flat_text(stmts: list[Stmt]) -> str:
    return " ".join(s.text + " " + _flat_text(s.body) + " " + _flat_text(s.orelse) for s in stmts)


def _c_function(fn: Stmt) -> FuncFacts:
    facts = FuncFacts(name=fn.name)
    facts.loop_cost, facts.loop_depth = _c_cost(fn.body, ONE, 0, facts, fn.name)
    body_text = _flat_text(fn.body)
    calls = re.findall(rf"\b{re.escape(fn.name)}\s*\((.*?)\)", body_text)
    if calls:
        facts.self_calls = max(1, _c_calls_on_path(fn.body, fn.name))
        facts.shrink = shrink_kind(" ".join(calls), set(re.findall(r"\w+", fn.text)), len(calls))
        facts.memo = bool(MEMO_RX.search(body_text))
    if _C_ALLOC_RX.search(body_text):
        facts.alloc = N
    return facts


def _c_calls_on_path(stmts: list[Stmt], name: str) -> int:
    rx = re.compile(rf"\b{re.escape(name)}\s*\(")
    total = 0
    for s in stmts:
        if s.kind == "if":
            total += len(rx.findall(s.text)) + max(_c_calls_on_path(s.body, name), _c_calls_on_path(s.orelse, name))
        else:
            total += len(rx.findall(s.text)) + _c_calls_on_path(s.body, name)
    return total


def _c_cost(stmts: list[Stmt], ctx: Cost, depth: int, facts: FuncFacts, name: str) -> tuple[Cost, int]:
    best, max_depth = ctx, depth
    for s in stmts:
        if s.kind == "loop":
            inner = _flat_text(s.body)
            if HALVING_RX.search(s.text) or (s.text.startswith("while") and HALVING_RX.search(inner)):
                factor = LOG
            elif re.search(r"(graph|adj\w*|neighbo\w*)\s*\[", s.text, re.I):
                factor, facts.graph = ONE, True
            elif re.fullmatch(r"for \w*\s*\w+\s*=\s*\d+;\s*\w+\s*<=?\s*\d+;.*", s.text):
                factor = ONE
            else:
                factor = N
            if depth == 0 and re.search(r"\b(return|break)\b", inner):
                facts.early_exit = True
            if re.search(rf"\b{re.escape(name)}\s*\(", inner):
                facts.call_in_loop = True
            cost, d = _c_cost(s.body, ctx * factor, depth + 1, facts, name)
        else:
            cost, d = _c_cost(s.body + s.orelse, ctx, depth, facts, name)
            if re.search(r"\bsort\s*\(|\.sort\(|sort\.\w+\(", s.text):
                cost = max(cost, ctx * NLOGN)
        best, max_depth = max(best, cost), max(max_depth, d)
    return best, max_depth
