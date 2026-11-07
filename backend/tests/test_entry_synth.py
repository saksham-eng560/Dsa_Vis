import ast

from core.entry_synth import synthesize_entry_call


def call(code: str):
    return synthesize_entry_call(ast.parse(code))


def test_picks_root_function_and_guesses_args() -> None:
    code = "def helper(a, i, j):\n    pass\ndef binary_search(arr, target):\n    helper(arr, 0, 1)\n"
    assert call(code) == ("binary_search([1, 3, 5, 7, 9, 11, 13], 7)", None)


def test_code_with_top_level_call_needs_nothing() -> None:
    assert call("def f(n):\n    return n\nprint(f(3))\n") == (None, None)


def test_unknown_params_warn() -> None:
    entry, warning = call("def f(widget):\n    return widget\n")
    assert entry is None and "f(widget)" in warning
