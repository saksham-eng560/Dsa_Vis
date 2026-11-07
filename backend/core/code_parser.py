"""Language detection and lightweight source preprocessing.

Detection is a weighted keyword vote — cheap, deterministic, and good enough to
pick a parser. The frontend runs an equivalent detector for instant feedback.
"""

import ast
import re

# (pattern, weight) votes per language. Patterns are anchored to idioms that are
# rare in the other supported languages.
_SIGNALS: dict[str, list[tuple[str, int]]] = {
    "python": [
        (r"^\s*def \w+\(.*\)\s*(->\s*[\w\[\], ]+)?:\s*$", 5),
        (r"^\s*(elif|except|finally)\b.*:\s*$", 4),
        (r"^\s*for \w+(, ?\w+)* in .+:\s*$", 4),
        (r"^\s*(import \w+|from [\w.]+ import)", 2),
        (r"\bprint\(", 1),
        (r"\b(None|True|False|self)\b", 1),
    ],
    "javascript": [
        (r"\bfunction\s*\w*\s*\(", 3),
        (r"\b(const|let|var)\s+\w+\s*=", 2),
        (r"=>", 2),
        (r"console\.log\(", 4),
        (r"===|!==", 2),
    ],
    "typescript": [
        (r"\b(interface|type)\s+\w+\s*[={]", 4),
        (r"\w+\s*:\s*(number|string|boolean|void|any)(\[\])?\b", 4),
        (r"\bas\s+(number|string|const)\b", 2),
    ],
    "cpp": [
        (r"#include\s*<", 6),
        (r"\bstd::", 4),
        (r"\b(cout|cin)\s*(<<|>>)", 4),
        (r"\bvector<", 3),
        (r"\b(int|void|bool)\s+\w+\s*\(.*\)\s*\{", 2),
    ],
    "java": [
        (r"\bpublic\s+(static\s+)?(class|void|int)\b", 5),
        (r"System\.out\.print", 6),
        (r"\b(ArrayList|HashMap|String\[\])\b", 3),
    ],
    "go": [
        (r"^\s*package\s+\w+", 6),
        (r"\bfunc\s+(\(\w+ \*?\w+\)\s*)?\w+\(", 5),
        (r":=", 2),
        (r"\bfmt\.Print", 4),
    ],
    "rust": [
        (r"\bfn\s+\w+\s*(<.*>)?\s*\(", 5),
        (r"\blet\s+mut\b", 5),
        (r"\b(println!|vec!)", 5),
        (r"->\s*(i32|i64|usize|bool|Vec<)", 3),
    ],
}

_COMPILED = {
    lang: [(re.compile(p, re.MULTILINE), w) for p, w in sigs] for lang, sigs in _SIGNALS.items()
}


def detect_language(code: str) -> str:
    """Return the most likely language for `code` (defaults to python)."""
    scores = {
        lang: sum(w * len(rx.findall(code)) for rx, w in sigs) for lang, sigs in _COMPILED.items()
    }
    # TypeScript is a JS superset: TS-only signals push JS code over to TS.
    if scores["typescript"] > 0:
        scores["typescript"] += scores["javascript"]
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "python" if is_valid_python(code) else "javascript"
    return best


def is_valid_python(code: str) -> bool:
    """True when `code` parses as Python."""
    try:
        ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    return True


def parse_python(code: str) -> ast.Module | None:
    """Parse Python source; returns None on syntax errors."""
    try:
        return ast.parse(code)
    except (SyntaxError, ValueError):
        return None


_STRING_RX = re.compile(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`')
_BLOCK_COMMENT_RX = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RX = re.compile(r"//[^\n]*")


def strip_c_like(code: str) -> str:
    """Blank out comments and string literals in C-family code, preserving line numbers.

    Strings become `""` so structure-scanning regexes don't match inside them.
    """

    def blank(match: re.Match[str]) -> str:
        text = match.group(0)
        return "\n" * text.count("\n")

    code = _BLOCK_COMMENT_RX.sub(blank, code)
    code = _STRING_RX.sub(lambda m: '""' + "\n" * m.group(0).count("\n"), code)
    return _LINE_COMMENT_RX.sub("", code)
