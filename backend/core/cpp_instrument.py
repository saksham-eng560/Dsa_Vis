"""Instrument C++ source for native step tracing.

Inserts `codelens_rt::step(LINE, "x", x, ...)` before each statement inside
function bodies, passing every variable known to be in scope, plus a
`codelens_rt::Frame` at each function entry. Insertions stay on the original
line, so line numbers (and compiler diagnostics) are unchanged.

Safety rules — the instrumentation must never change program meaning:
* only insert where a statement may start: after `{`, `;` or `}` (never as the
  sole body of a brace-less `if`/`for`/`else`);
* only pass variables that are definitely initialised (declared with an
  initialiser, containers, parameters, class members);
* never pass lambdas / std::function objects.
"""

import re

from core.c_parser import CParser, Stmt

_KEYWORDS = {
    "return", "delete", "throw", "else", "goto", "case", "using", "typedef", "new", "co_return",
    "break", "continue", "if", "for", "while", "switch", "do", "public", "private", "protected", "default",
    "operator", "sizeof", "static_assert", "template", "friend", "namespace",
}
_ACCESS_RX = re.compile(r"^\s*(public|private|protected)\s*:\s*")
_MULTIWORD_RX = re.compile(
    r"^((?:const|static|constexpr)\s+)*(?:(?:unsigned|signed|long|short)\s+)+(?:int|double|char\b)?\s*"
)
_DECL_RX = re.compile(
    r"^(?:(?:const|static|constexpr|mutable|inline|volatile)\s+)*"
    r"(?P<type>[A-Za-z_][\w:]*(?:\s*<.*>)?)(?P<ptr>\s*[*&]+\s*|\s+)(?P<name>[A-Za-z_]\w*)\s*(?P<rest>.*)$",
    re.S,
)
_CONTAINERS = re.compile(r"vector|map|set|string|deque|queue|stack|list|array|priority_queue|pair|bitset")
_SKIP_TYPES = re.compile(r"function\s*<|\bauto\b.*=\s*\[|^\s*auto\s*&?\s*\w+\s*=\s*\[")
_STRUCT_BIND_RX = re.compile(r"auto\s*&{0,2}\s*\[([^\]]+)\]")


def _top_level_split(text: str, sep: str = ",") -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def declared_vars(text: str) -> list[str]:
    """Names declared (and safely initialised) by a simple statement, else []."""
    text = _ACCESS_RX.sub("", text).strip().rstrip(";").strip()
    if not text or text.startswith("#") or _SKIP_TYPES.search(text):
        return []
    text = _MULTIWORD_RX.sub(lambda m: (m.group(1) or "") + "int ", text)  # long long x → int x
    if m := _STRUCT_BIND_RX.match(text):
        return [n.strip() for n in m.group(1).split(",") if n.strip().isidentifier()]
    m = _DECL_RX.match(text)
    if not m:
        return []
    type_, name, rest = m.group("type").strip(), m.group("name"), m.group("rest").strip()
    first_word = type_.split("<")[0].split("::")[-1].strip("*& ")
    if first_word in _KEYWORDS or type_ in _KEYWORDS or name in _KEYWORDS:
        return []
    if rest and rest[0] not in "=({,[" :
        return []  # e.g. `a < b` or a call — not a declaration
    initialised = bool(rest) and rest[0] in "=({"
    names = [name] if initialised or (_CONTAINERS.search(type_) and "*" not in type_ + m.group("ptr")) else []
    # further declarators: `int a = 1, b = 2`
    for extra in _top_level_split(rest)[1:] if "," in rest else []:
        if em := re.match(r"^[*&]*\s*([A-Za-z_]\w*)\s*[=({]", extra):
            names.append(em.group(1))
    return names


def loop_vars(header: str) -> list[str]:
    """Variables a `for` header introduces: `for (int i = 0; …)` / `for (auto& [k, v] : m)`."""
    inner = header.removeprefix("for").strip()
    if ":" in inner and ";" not in inner:  # range-based for
        decl = inner.split(":")[0]
        if m := _STRUCT_BIND_RX.search(decl):
            return [n.strip() for n in m.group(1).split(",")]
        m = re.search(r"([A-Za-z_]\w*)\s*$", decl.strip())
        return [m.group(1)] if m else []
    first = inner.split(";")[0]
    return declared_vars(first) if first.strip() else []


def param_vars(signature: str) -> list[str]:
    m = re.search(r"\(([^()]*)\)\s*(?:const\s*)?(?:override\s*)?(?:noexcept\s*)?(?:->.*)?$", signature.strip())
    if not m:
        return []
    names = []
    for part in _top_level_split(m.group(1)):
        part = part.split("=")[0].strip()
        if "(" in part or not part:
            continue
        tokens = re.sub(r"[*&]|\[\s*\]", " ", re.sub(r"<.*>", "<>", part)).split()
        if len(tokens) >= 2 and tokens[-1].isidentifier() and tokens[-1] not in _KEYWORDS:
            names.append(tokens[-1])
    return names


class _Instrumenter:
    def __init__(self, code: str) -> None:
        self.code = code
        self.parser = CParser(code)
        self.src = self.parser.src  # comment/string-stripped, same length as code
        self.inserts: list[tuple[int, str]] = []

    def _safe(self, pos: int) -> bool:
        i = pos - 1
        while i >= 0 and self.src[i] in " \t\r\n":
            i -= 1
        return i < 0 or self.src[i] in "{;}"

    def _step(self, line: int, scope: list[str]) -> str:
        names = list(dict.fromkeys(scope))
        args = "".join(f', "{n}", {n}' for n in names)
        return f"codelens_rt::step({line}{args}); "

    def run(self) -> str | None:
        top = self.parser.parse()
        globals_: list[str] = []
        for stmt in top:
            if stmt.kind == "func":
                self._func(stmt, globals_)
            elif stmt.kind == "block":
                members = [n for m in stmt.members for n in declared_vars(m.text)]
                for fn in stmt.body:
                    if fn.kind == "func":
                        self._func(fn, globals_ + members)
            elif stmt.kind == "simple":
                globals_ += declared_vars(stmt.text)
        return self.inserts and self._apply() or None

    def _func(self, fn: Stmt, outer: list[str]) -> None:
        if fn.body_pos < 0:
            return
        self.inserts.append((fn.body_pos, f'codelens_rt::Frame codelens_frame_("{fn.name}"); '))
        self._block(fn.body, outer + param_vars(fn.text))

    def _block(self, stmts: list[Stmt], scope: list[str]) -> None:
        local = list(scope)
        for s in stmts:
            if s.pos >= 0 and s.kind != "func" and self._safe(s.pos):
                self.inserts.append((s.pos, self._step(s.line, local)))
            if s.kind in ("simple", "io"):
                local += declared_vars(s.text)
            elif s.kind == "loop":
                inner = local + (loop_vars(s.text) if s.text.startswith("for") else [])
                if s.body_pos >= 0:
                    self.inserts.append((s.body_pos, self._step(s.line, inner)))
                    self._block(s.body, inner)
                else:
                    self._braceless(s.body, inner, s.line)
            elif s.kind == "if":
                self._branch(s.body, s.body_pos, local)
                if s.orelse:
                    self._branch(s.orelse, s.orelse_pos, local)
            elif s.kind == "block":
                self._block(s.body, local)

    def _branch(self, body: list[Stmt], body_pos: int, scope: list[str]) -> None:
        if body_pos >= 0:
            self._block(body, scope)
        else:
            self._braceless(body, scope, None)

    def _braceless(self, body: list[Stmt], scope: list[str], line: int | None) -> None:
        """Wrap a brace-less single-statement body: `stmt` → `{ step(...); stmt }` (same meaning)."""
        if len(body) != 1 or body[0].pos < 0 or body[0].end < 0 or body[0].kind == "func":
            return
        child = body[0]
        self.inserts.append((child.pos, "{ " + self._step(line or child.line, scope)))
        self.inserts.append((child.end, " }", 0))  # type: ignore[arg-type]
        self._block_children(child, scope)

    def _block_children(self, s: Stmt, scope: list[str]) -> None:
        """Recurse into a statement's nested bodies without instrumenting the statement itself."""
        if s.kind == "loop":
            inner = scope + (loop_vars(s.text) if s.text.startswith("for") else [])
            if s.body_pos >= 0:
                self.inserts.append((s.body_pos, self._step(s.line, inner)))
                self._block(s.body, inner)
            else:
                self._braceless(s.body, inner, s.line)
        elif s.kind == "if":
            self._branch(s.body, s.body_pos, scope)
            if s.orelse:
                self._branch(s.orelse, s.orelse_pos, scope)
        elif s.kind == "block":
            self._block(s.body, scope)

    def _apply(self) -> str:
        code = self.code
        # same position: apply steps before closing braces so the result reads `} step(...)`
        ordered = sorted(((t[0], t[2] if len(t) > 2 else 1, t[1]) for t in self.inserts), reverse=True)
        for pos, _, text in ordered:
            code = code[:pos] + text + code[pos:]
        return code


def instrument(code: str) -> str | None:
    """Instrumented source, or None when nothing could be instrumented."""
    return _Instrumenter(code).run()
