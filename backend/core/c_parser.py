"""Tiny structural parser for C-family languages (JS/TS/C++/Java/Go/Rust).

It is NOT a full parser: it recognises functions, if/else, loops, return,
break/continue and treats everything else as a simple statement. That is all
the flowchart and complexity heuristics need, and it degrades gracefully on
syntax it does not understand.
"""

import re
from dataclasses import dataclass, field

from core.code_parser import strip_c_like

_CONTROL = {"if", "for", "while", "switch", "catch", "else", "do", "loop", "try"}
_IO_RX = re.compile(r"\b(console\.log|printf|println!?|print!?|cout|cin|System\.out|fmt\.Print\w*|scanf|puts)\b")
_FUNC_RX = re.compile(
    r"(?:fn|func|function)\s+(?:\([^)]*\)\s*)?(\w+)"  # Rust / Go (incl. receiver) / JS keyword
    r"|(\w+)\s*(?:=\s*(?:async\s*)?)?\([^()]*\)\s*(?:->\s*[\w<>\[\], &]+|:\s*[\w<>\[\]| ]+)?\s*(?:=>)?\s*$"
    r"|(\w+)\s*\([^()]*\)\s*(?:const\s*)?(?:throws [\w, ]+)?$"  # C++ / Java signatures
)


@dataclass
class Stmt:
    """Structural IR node."""

    kind: str  # simple | io | if | loop | return | break | continue | func | block
    text: str
    line: int
    body: list["Stmt"] = field(default_factory=list)
    orelse: list["Stmt"] = field(default_factory=list)
    name: str = ""
    pos: int = -1  # source offset where the statement starts
    body_pos: int = -1  # offset just after the body's `{` (-1: no braced body)
    members: list["Stmt"] = field(default_factory=list)  # class/struct non-function members
    end: int = -1  # source offset just after the statement
    orelse_pos: int = -1  # offset after the else-body's `{` (-1: brace-less or no else)


class CParser:
    """Recursive-descent over comment/string-stripped source."""

    def __init__(self, code: str) -> None:
        self.src = strip_c_like(code)
        self.pos = 0
        self.line_starts = [0] + [i + 1 for i, ch in enumerate(self.src) if ch == "\n"]

    def line_of(self, pos: int) -> int:
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def parse(self) -> list[Stmt]:
        return self.block(top=True)

    def _skip_ws(self) -> None:
        while self.pos < len(self.src) and self.src[self.pos] in " \t\r\n;":
            self.pos += 1

    def _peek_word(self) -> str:
        m = re.match(r"[A-Za-z_]\w*", self.src[self.pos:])
        return m.group(0) if m else ""

    def block(self, top: bool = False) -> list[Stmt]:
        out: list[Stmt] = []
        while True:
            self._skip_ws()
            if self.pos >= len(self.src) or self.src[self.pos] == "}":
                if self.pos < len(self.src) and not top:
                    self.pos += 1
                elif self.pos < len(self.src):
                    self.pos += 1  # stray brace at top level
                    continue
                return out
            stmt = self.statement()
            if stmt:
                out.append(stmt)

    def _balanced(self, open_ch: str, close_ch: str) -> str:
        """Consume a balanced group starting at `open_ch`; return inner text."""
        depth, start = 0, self.pos
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            depth += ch == open_ch
            depth -= ch == close_ch
            self.pos += 1
            if depth == 0:
                return self.src[start + 1 : self.pos - 1]
        return self.src[start + 1 :]

    def _header(self) -> str:
        """Text up to the body: `( … )` group, or up to `{` at depth 0."""
        self._skip_inline_ws()
        if self.pos < len(self.src) and self.src[self.pos] == "(":
            return self._balanced("(", ")").strip()
        start, depth = self.pos, 0
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            elif ch == "{" and depth == 0:
                break
            self.pos += 1
        return self.src[start : self.pos].strip()

    def _skip_inline_ws(self) -> None:
        while self.pos < len(self.src) and self.src[self.pos] in " \t\r\n":
            self.pos += 1

    def _body(self) -> list[Stmt]:
        return self._body_at()[0]

    def _body_at(self) -> tuple[list[Stmt], int]:
        """Parse a braced block or a single statement; also return the offset after `{`."""
        self._skip_inline_ws()
        if self.pos < len(self.src) and self.src[self.pos] == "{":
            self.pos += 1
            body_pos = self.pos
            return self.block(), body_pos
        stmt = self.statement()
        return ([stmt] if stmt else []), -1

    def statement(self) -> Stmt | None:
        start = self.pos
        stmt = self._statement()
        if stmt is not None and stmt.pos < 0:
            stmt.pos = start
        if stmt is not None:
            stmt.end = self.pos
        return stmt

    def _statement(self) -> Stmt | None:
        start = self.pos
        line = self.line_of(start)
        word = self._peek_word()
        if word in ("if", "while", "for", "switch"):
            self.pos += len(word)
            header = self._header()
            body, body_pos = self._body_at()
            if word == "if":
                orelse: list[Stmt] = []
                orelse_pos = -1
                save = self.pos
                self._skip_inline_ws()
                if self._peek_word() == "else":
                    self.pos += 4
                    orelse, orelse_pos = self._body_at()
                else:
                    self.pos = save  # keep `end` right after the if-body
                return Stmt("if", header, line, body, orelse, body_pos=body_pos, orelse_pos=orelse_pos)
            if word == "switch":
                return Stmt("block", f"switch ({header})", line, body)
            return Stmt("loop", f"{word} {header}", line, body, body_pos=body_pos)
        if word in ("do", "loop", "try"):
            self.pos += len(word)
            body = self._body()
            if word == "do":
                self._skip_inline_ws()
                if self._peek_word() == "while":
                    self.pos += 5
                    cond = self._header()
                    return Stmt("loop", f"do … while {cond}", line, body)
            if word == "try":
                return Stmt("block", "try", line, body)
            return Stmt("loop", "loop", line, body)
        if word in ("break", "continue"):
            self._simple_text()
            return Stmt(word, word, line)
        if word in ("catch", "finally"):
            self.pos += len(word)
            header = self._header()
            return Stmt("block", f"{word} {header}".strip(), line, self._body())
        return self._simple_or_function(line)

    def _simple_text(self) -> tuple[str, bool]:
        """Consume a simple statement. Returns (text, ended_with_block)."""
        start, depth = self.pos, 0
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            elif ch == "{" and depth == 0:
                return self.src[start : self.pos].strip(), True
            elif ch == "}" and depth <= 0:
                break
            elif ch == ";" and depth == 0 or ch == "\n" and depth == 0 and self._line_complete(start):
                self.pos += 1
                break
            self.pos += 1
        return self.src[start : self.pos].strip().rstrip(";").strip(), False

    def _line_complete(self, start: int) -> bool:
        """Heuristic statement end at newline (Go / semicolon-less JS)."""
        text = self.src[start : self.pos].rstrip()
        return not text or not text.endswith(("=", "+", "-", "*", "/", ",", "&&", "||", ".", "(", "?", ":"))

    def _simple_or_function(self, line: int) -> Stmt | None:
        text, has_block = self._simple_text()
        if has_block:
            word = text.split(" ", 1)[0] if text else ""
            m = _FUNC_RX.search(text)
            is_container = re.match(r"(?:\w+\s+)*(class|struct|impl|namespace|interface|enum|object)\b", text)
            if m and not is_container and word not in _CONTROL:
                self.pos += 1
                name = next(g for g in m.groups() if g)
                body_pos = self.pos
                return Stmt("func", text, line, self.block(), name=name, body_pos=body_pos)
            # object literal / initializer / class body: recurse to find nested functions
            self.pos += 1
            inner = self.block()
            funcs = [s for s in inner if s.kind == "func"]
            if funcs:
                return Stmt("block", text, line, funcs, members=[s for s in inner if s.kind != "func"])
            self._simple_text()  # swallow the rest, e.g. `;` after `x = {…}`
            return Stmt("simple", text + " {…}", line)
        if not text:
            if self.pos < len(self.src) and self.src[self.pos] == "}":
                return None
            self.pos += 1
            return None
        if text.startswith("return") or text.startswith("throw"):
            return Stmt("return", text, line)
        return Stmt("io" if _IO_RX.search(text) else "simple", text, line)
