from core.json_utils import extract_json


def test_fenced_with_trailing_comma() -> None:
    assert extract_json('Here:\n```json\n{"a": [1, 2,],}\n```') == {"a": [1, 2]}


def test_truncated_object_is_closed() -> None:
    assert extract_json('{"summary": "ok", "edge_cases": ["x"], "optimiz') == {
        "summary": "ok", "edge_cases": ["x"]}


def test_escaped_quotes_inside_strings() -> None:
    assert extract_json('{"s": "say \\"hi\\" {not a brace}"}') == {"s": 'say "hi" {not a brace}'}


def test_garbage_returns_none() -> None:
    assert extract_json("no json here") is None
    assert extract_json("") is None
