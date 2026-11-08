"""C-family structural IR (`c_parser.Stmt`) → flowchart."""

import re

from api.schemas.response import Flowchart
from core.c_parser import CParser, Stmt
from core.flow_builder import PROGRAM_GROUP, FlowBuilder, Pending

_PREAMBLE_RX = re.compile(r"\s*(#|import\b|package\b|using\b|use\b|export\s+\{|\"use strict\")")


def _short(text: str, limit: int = 48) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def c_flowchart(code: str) -> Flowchart:
    """Flowchart for each function found in C-family `code` (+ top-level code)."""
    stmts = CParser(code).parse()
    builder = FlowBuilder()
    funcs: list[Stmt] = []
    top: list[Stmt] = []
    for stmt in stmts:
        if stmt.kind == "func":
            funcs.append(stmt)
        elif stmt.kind == "block" and all(s.kind == "func" for s in stmt.body) and stmt.body:
            funcs.extend(stmt.body)  # class / impl / namespace members
        elif not _PREAMBLE_RX.match(stmt.text):
            top.append(stmt)
    for func in funcs:
        _Walker(builder, func.name).function(func.body, _short(func.text, 40), func.line)
    if top:
        _Walker(builder, PROGRAM_GROUP).function(top, "Program start", top[0].line)
    return Flowchart(nodes=builder.nodes, edges=builder.edges, source="static")


class _Walker:
    def __init__(self, builder: FlowBuilder, group: str) -> None:
        self.b = builder
        self.group = group
        self.loops: list[tuple[str, list[Pending]]] = []
        self.end_id = ""

    def function(self, body: list[Stmt], title: str, line: int) -> None:
        start = self.b.node("start", title, self.group, line)
        self.end_id = self.b.node("end", "End", self.group, None)
        self.b.connect(self.block(body, [(start, None)]), self.end_id)

    def block(self, stmts: list[Stmt], preds: list[Pending]) -> list[Pending]:
        run: list[Stmt] = []
        for stmt in stmts:
            if stmt.kind == "simple" and len(run) < 3:
                run.append(stmt)
                continue
            preds, run = self._flush(run, preds), []
            if stmt.kind == "simple":
                run.append(stmt)
                continue
            preds = self.statement(stmt, preds)
        return self._flush(run, preds)

    def _flush(self, run: list[Stmt], preds: list[Pending]) -> list[Pending]:
        if not run:
            return preds
        label = "\n".join(_short(s.text) for s in run)
        nid = self.b.node("process", label, self.group, run[0].line, run[-1].line)
        self.b.connect(preds, nid)
        return [(nid, None)]

    def _add(self, kind: str, label: str, line: int, preds: list[Pending]) -> str:
        nid = self.b.node(kind, _short(label), self.group, line)  # type: ignore[arg-type]
        self.b.connect(preds, nid)
        return nid

    def statement(self, stmt: Stmt, preds: list[Pending]) -> list[Pending]:
        if stmt.kind == "if":
            dec = self._add("decision", f"{stmt.text} ?", stmt.line, preds)
            then = self.block(stmt.body, [(dec, "True")])
            other = self.block(stmt.orelse, [(dec, "False")]) if stmt.orelse else [(dec, "False")]
            return then + other
        if stmt.kind == "loop":
            head = self._add("decision", stmt.text, stmt.line, preds)
            self.loops.append((head, []))
            self.b.connect(self.block(stmt.body, [(head, "True")]), head)
            _, breaks = self.loops.pop()
            return [(head, "False")] + breaks
        if stmt.kind == "return":
            nid = self._add("io", stmt.text, stmt.line, preds)
            self.b.connect([(nid, None)], self.end_id)
            return []
        if stmt.kind == "break" and self.loops:
            self.loops[-1][1].extend(preds)
            return []
        if stmt.kind == "continue" and self.loops:
            self.b.connect(preds, self.loops[-1][0], "continue")
            return []
        if stmt.kind == "block":
            nid = self._add("process", stmt.text, stmt.line, preds)
            return self.block(stmt.body, [(nid, None)])
        if stmt.kind == "func":  # nested function: show as a definition step
            return [(self._add("process", f"define {stmt.name}", stmt.line, preds), None)]
        return [(self._add("io" if stmt.kind == "io" else "process", stmt.text, stmt.line, preds), None)]
