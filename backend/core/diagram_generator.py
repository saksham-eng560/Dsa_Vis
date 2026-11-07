"""Python AST → flowchart (control-flow graph of structured code).

Each function becomes its own `group`; top-level statements form `PROGRAM_GROUP`.
Nodes carry source line ranges so the frontend can light up the node matching
the current dry-run line.
"""

import ast

from api.schemas.response import Flowchart, FlowEdge, FlowNode
from core.flow_builder import PROGRAM_GROUP, FlowBuilder, Pending

_IO_CALLS = {"print", "input", "write", "read", "readline"}


def python_flowchart(tree: ast.Module, code: str) -> Flowchart:
    """Build a flowchart for every function plus module-level code."""
    builder = FlowBuilder()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = ", ".join(a.arg for a in node.args.args)
            _PyWalker(builder, code, node.name).function(node.body, f"{node.name}({args})", node.lineno)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    group = f"{node.name}.{item.name}"
                    _PyWalker(builder, code, group).function(item.body, group, item.lineno)
    top = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                       ast.ClassDef, ast.Import, ast.ImportFrom))]
    if top:
        _PyWalker(builder, code, PROGRAM_GROUP).function(top, "Program start", top[0].lineno)
    return Flowchart(nodes=builder.nodes, edges=builder.edges, source="static")


class _PyWalker:
    """Walks one function body, emitting nodes into a shared FlowBuilder."""

    def __init__(self, builder: FlowBuilder, code: str, group: str) -> None:
        self.b = builder
        self.code = code
        self.group = group
        self.loops: list[tuple[str, list[Pending]]] = []  # (header id, break exits)
        self.end_id = ""

    def function(self, body: list[ast.stmt], title: str, line: int) -> None:
        start = self.b.node("start", title, self.group, line)
        self.end_id = self.b.node("end", "End", self.group, None)
        exits = self.block(body, [(start, None)])
        self.b.connect(exits, self.end_id)

    def _src(self, node: ast.AST, limit: int = 48) -> str:
        text = (ast.get_source_segment(self.code, node) or ast.unparse(node)).split("\n")[0]
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def block(self, stmts: list[ast.stmt], preds: list[Pending]) -> list[Pending]:
        """Emit `stmts` in sequence; returns dangling exits."""
        simple: list[ast.stmt] = []
        for stmt in stmts:
            if self._is_simple(stmt):
                simple.append(stmt)
                if len(simple) == 3:
                    preds, simple = self._flush(simple, preds), []
                continue
            preds, simple = self._flush(simple, preds), []
            preds = self.statement(stmt, preds)
        return self._flush(simple, preds)

    def _is_simple(self, stmt: ast.stmt) -> bool:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return not self._is_io(stmt.value)
        return isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Pass,
                                 ast.Delete, ast.Global, ast.Nonlocal, ast.Assert))

    def _is_io(self, call: ast.Call) -> bool:
        func = call.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        return name in _IO_CALLS

    def _flush(self, simple: list[ast.stmt], preds: list[Pending]) -> list[Pending]:
        if not simple:
            return preds
        label = "\n".join(self._src(s) for s in simple)
        nid = self.b.node("process", label, self.group, simple[0].lineno, simple[-1].end_lineno)
        self.b.connect(preds, nid)
        return [(nid, None)]

    def statement(self, stmt: ast.stmt, preds: list[Pending]) -> list[Pending]:
        """Emit one compound/control statement."""
        if isinstance(stmt, ast.If):
            dec = self._decision(f"{self._src(stmt.test)} ?", stmt, preds)
            then = self.block(stmt.body, [(dec, "True")])
            other = self.block(stmt.orelse, [(dec, "False")]) if stmt.orelse else [(dec, "False")]
            return then + other
        if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            return self._loop(stmt, preds)
        if isinstance(stmt, ast.Return):
            label = f"return {self._src(stmt.value)}" if stmt.value else "return"
            nid = self.b.node("io", label, self.group, stmt.lineno)
            self.b.connect(preds, nid)
            self.b.connect([(nid, None)], self.end_id)
            return []
        if isinstance(stmt, ast.Raise):
            nid = self.b.node("end", f"raise {self._src(stmt.exc) if stmt.exc else ''}".strip(),
                              self.group, stmt.lineno)
            self.b.connect(preds, nid)
            return []
        if isinstance(stmt, ast.Break) and self.loops:
            self.loops[-1][1].extend(preds)
            return []
        if isinstance(stmt, ast.Continue) and self.loops:
            self.b.connect(preds, self.loops[-1][0], "continue")
            return []
        if isinstance(stmt, ast.Try):
            return self._try(stmt, preds)
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            nid = self._plain("process", f"with {self._src(stmt.items[0].context_expr)}", stmt, preds)
            return self.block(stmt.body, [(nid, None)])
        kind = "io" if isinstance(stmt, ast.Expr) else "process"
        return [(self._plain(kind, self._src(stmt), stmt, preds), None)]

    def _plain(self, kind: str, label: str, stmt: ast.stmt, preds: list[Pending]) -> str:
        nid = self.b.node(kind, label, self.group, stmt.lineno)  # type: ignore[arg-type]
        self.b.connect(preds, nid)
        return nid

    def _decision(self, label: str, stmt: ast.stmt, preds: list[Pending]) -> str:
        return self._plain("decision", label, stmt, preds)

    def _loop(self, stmt: ast.For | ast.AsyncFor | ast.While, preds: list[Pending]) -> list[Pending]:
        if isinstance(stmt, ast.While):
            label = f"while {self._src(stmt.test)} ?"
            yes, no = "True", "False"
        else:
            label = f"for {self._src(stmt.target)} in {self._src(stmt.iter)}"
            yes, no = "next", "done"
        head = self._decision(label, stmt, preds)
        self.loops.append((head, []))
        body_exits = self.block(stmt.body, [(head, yes)])
        self.b.connect(body_exits, head, None)
        _, breaks = self.loops.pop()
        exits: list[Pending] = [(head, no)]
        if stmt.orelse:
            exits = self.block(stmt.orelse, exits)
        return exits + breaks

    def _try(self, stmt: ast.Try, preds: list[Pending]) -> list[Pending]:
        head = self._plain("process", "try", stmt, preds)
        exits = self.block(stmt.body, [(head, None)])
        for handler in stmt.handlers:
            name = self._src(handler.type) if handler.type else "Exception"
            exits += self.block(handler.body, [(head, f"except {name}")])
        if stmt.finalbody:
            exits = self.block(stmt.finalbody, exits)
        return exits


__all__ = ["python_flowchart", "FlowEdge", "FlowNode"]
