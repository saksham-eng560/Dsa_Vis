import pytest

from core.code_parser import detect_language, strip_c_like

SAMPLES = {
    "python": "def f(xs):\n    for x in xs:\n        print(x)\n",
    "javascript": "function f(a) {\n  const b = a.map(x => x * 2);\n  console.log(b);\n}",
    "typescript": "function f(a: number[]): number {\n  let s: number = 0;\n  return s;\n}",
    "cpp": "#include <vector>\nint main() {\n  std::vector<int> v;\n  std::cout << v.size();\n}",
    "java": "public class Main {\n  public static void main(String[] args) {\n    System.out.println(1);\n  }\n}",
    "go": "package main\nimport \"fmt\"\nfunc main() {\n  x := 1\n  fmt.Println(x)\n}",
    "rust": "fn main() {\n    let mut v = vec![1, 2];\n    println!(\"{:?}\", v);\n}",
}


@pytest.mark.parametrize("lang,code", SAMPLES.items())
def test_detect_language(lang: str, code: str) -> None:
    assert detect_language(code) == lang


def test_strip_c_like_preserves_lines() -> None:
    code = 'int a = 1; // c\n/* multi\nline */ char* s = "for (;;) {";\n'
    out = strip_c_like(code)
    assert out.count("\n") == code.count("\n")
    assert "for" not in out and "multi" not in out
