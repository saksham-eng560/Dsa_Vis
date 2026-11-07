"""C++ support for LeetCode mode: type mapping, starter code and a generated
test driver. Inputs are embedded as C++ literals at generation time, so the
driver needs no runtime parser; results are printed as JSON after a marker.
"""

import json
import re
from typing import Any

from api.schemas.leetcode import LCParam, LCProblem
from core.lc_runtime import TestInputError, parse_value

RESULT_MARKER = "@@CODELENS_RESULT@@"

_SCALARS = {
    "integer": "int", "long": "long long", "double": "double", "float": "double", "boolean": "bool",
    "string": "string", "character": "char", "void": "void",
    "ListNode": "ListNode*", "TreeNode": "TreeNode*",
}


def _norm(lc_type: str) -> tuple[str, int]:
    """("integer", 2) for "integer[][]" / "list<list<integer>>"."""
    depth = 0
    while True:
        if m := re.fullmatch(r"list<(.+)>", lc_type):
            lc_type, depth = m.group(1), depth + 1
        elif lc_type.endswith("[]"):
            lc_type, depth = lc_type[:-2], depth + 1
        else:
            return lc_type, depth


def cpp_type(lc_type: str) -> str:
    base, depth = _norm(lc_type)
    if base not in _SCALARS:
        raise TestInputError(f"C++ mode doesn't support the LeetCode type `{lc_type}` yet")
    out = _SCALARS[base]
    for _ in range(depth):
        out = f"vector<{out}>"
    return out


def _param_decl(p: LCParam) -> str:
    t = cpp_type(p.type)
    by_ref = t.startswith("vector") or t == "string"
    return f"{t}{'&' if by_ref else ''} {p.name}"


def cpp_starter(p: LCProblem) -> str:
    """LeetCode-style C++ skeleton."""
    header = ""
    types = " ".join(x.type for x in [*p.params, *p.constructor_params]) + p.return_type
    types += " ".join(pp.type for m in p.methods for pp in m.params)
    if "ListNode" in types:
        header += ("/**\n * struct ListNode {\n *     int val;\n *     ListNode *next;\n"
                   " *     ListNode(int x) : val(x), next(nullptr) {}\n * };\n */\n")
    if "TreeNode" in types:
        header += ("/**\n * struct TreeNode {\n *     int val;\n *     TreeNode *left;\n *     TreeNode *right;\n"
                   " *     TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}\n * };\n */\n")

    def method(name: str, params: list[LCParam], ret: str) -> str:
        args = ", ".join(_param_decl(x) for x in params)
        return f"    {cpp_type(ret)} {name}({args}) {{\n        \n    }}\n"

    if p.design:
        ctor = ", ".join(_param_decl(x) for x in p.constructor_params)
        body = f"    {p.class_name}({ctor}) {{\n        \n    }}\n"
        body += "".join("\n" + method(m.name, m.params, m.return_type) for m in p.methods)
        return f"{header}class {p.class_name} {{\npublic:\n{body}}};\n"
    return f"{header}class Solution {{\npublic:\n{method(p.function_name or 'solve', p.params, p.return_type)}}};\n"


# ------------------------------------------------------------- literals ----
def _str_lit(s: str) -> str:
    return "string(" + json.dumps(s, ensure_ascii=False) + ")"


def literal(value: Any, lc_type: str) -> str:
    """C++ expression constructing `value` as `lc_type`."""
    base, depth = _norm(lc_type)
    if depth:
        if not isinstance(value, list):
            raise TestInputError(f"expected a list for `{lc_type}`, got {json.dumps(value)}")
        inner = lc_type[:-2] if lc_type.endswith("[]") else re.fullmatch(r"list<(.+)>", lc_type).group(1)  # type: ignore[union-attr]
        return f"{cpp_type(lc_type)}{{{', '.join(literal(v, inner) for v in value)}}}"
    if base == "ListNode":
        return f"_lc_list({{{', '.join(str(int(v)) for v in value or [])}}})"
    if base == "TreeNode":
        cells = ", ".join('"null"' if v is None else f'"{int(v)}"' for v in value or [])
        return f"_lc_tree({{{cells}}})"
    if base == "boolean":
        return "true" if value else "false"
    if base == "string":
        return _str_lit(str(value))
    if base == "character":
        return "'" + json.dumps(str(value))[1:-1].replace("'", "\\'") + "'"
    if base == "double":
        return repr(float(value))
    if base == "long":
        return f"{int(value)}LL"
    if base == "integer":
        return str(int(value))
    raise TestInputError(f"C++ mode doesn't support the LeetCode type `{lc_type}` yet")


# --------------------------------------------------------------- driver ----
def _case(problem: LCProblem, lines: list[str]) -> str:
    """Body of one `case` in the driver's switch."""
    lines = [ln for ln in lines if ln.strip()]
    if problem.design:
        if len(lines) != 2:
            raise TestInputError("Design problems need 2 lines: the operations list and the arguments list")
        ops, args = parse_value(lines[0], "operations"), parse_value(lines[1], "arguments")
        methods = {m.name: m for m in problem.methods}
        code = [f"auto* obj = new {problem.class_name}("
                + ", ".join(literal(a, p.type) for a, p in zip(args[0], problem.constructor_params, strict=False))
                + ");", 'string out = "[null";']
        for op, arg in zip(ops[1:], args[1:], strict=True):
            m = methods.get(op)
            if m is None:
                raise TestInputError(f"Unknown method `{op}`")
            call = f"obj->{op}(" + ", ".join(literal(a, p.type) for a, p in zip(arg, m.params, strict=False)) + ")"
            code.append(f'{call}; out += ",null";' if m.return_type == "void" else f'out += "," + _json({call});')
        code.append('out += "]"; _emit_raw(out);')
        return "\n            ".join(code)
    if len(lines) != len(problem.params):
        raise TestInputError(f"Expected {len(problem.params)} input line(s), got {len(lines)}")
    decls = [f"{cpp_type(p.type)} {p.name} = {literal(parse_value(ln, p.name), p.type)};"
             for p, ln in zip(problem.params, lines, strict=True)]
    call = f"Solution().{problem.function_name}({', '.join(p.name for p in problem.params)})"
    if problem.output_param is not None:
        emit = f"{call}; _emit({problem.params[problem.output_param].name});"
    elif problem.return_type == "void":
        emit = f'{call}; _emit_raw("null");'
    else:
        emit = f"auto _r = {call}; _emit(_r);"
    return "\n            ".join([*decls, emit])


def build_driver(problem: LCProblem, user_code: str, tests: list[list[str]]) -> tuple[str, list[str | None]]:
    """Full translation unit + per-test input errors (None when the test is valid)."""
    cases, errors = [], []
    for i, lines in enumerate(tests):
        try:
            cases.append(f"        case {i}: {{\n            {_case(problem, lines)}\n            break;\n        }}")
            errors.append(None)
        except (TestInputError, ValueError, TypeError) as exc:
            errors.append(str(exc))
    main = (
        "int main(int argc, char** argv) {\n    ios::sync_with_stdio(false);\n"
        "    int _t = argc > 1 ? atoi(argv[1]) : 0;\n    try {\n        switch (_t) {\n"
        + "\n".join(cases)
        + "\n        }\n    } catch (const exception& e) {\n"
        '        cout.flush(); cerr << "Exception: " << e.what(); return 3;\n    }\n    return 0;\n}\n'
    )
    return f"{PRELUDE}\n#line 1 \"solution.cpp\"\n{user_code}\n#line 1 \"driver.cpp\"\n{main}", errors


PRELUDE = r'''#include <bits/stdc++.h>
using namespace std;

struct ListNode {
    int val; ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *n) : val(x), next(n) {}
};
struct TreeNode {
    int val; TreeNode *left; TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *l, TreeNode *r) : val(x), left(l), right(r) {}
};

static ListNode* _lc_list(const vector<int>& v) {
    ListNode dummy; ListNode* t = &dummy;
    for (int x : v) { t->next = new ListNode(x); t = t->next; }
    return dummy.next;
}
static TreeNode* _lc_tree(const vector<string>& v) {
    if (v.empty() || v[0] == "null") return nullptr;
    TreeNode* root = new TreeNode(stoi(v[0]));
    queue<TreeNode*> q; q.push(root); size_t i = 1;
    while (!q.empty() && i < v.size()) {
        TreeNode* n = q.front(); q.pop();
        if (i < v.size() && v[i] != "null") { n->left = new TreeNode(stoi(v[i])); q.push(n->left); } i++;
        if (i < v.size() && v[i] != "null") { n->right = new TreeNode(stoi(v[i])); q.push(n->right); } i++;
    }
    return root;
}

static string _json(int x) { return to_string(x); }
static string _json(long x) { return to_string(x); }
static string _json(long long x) { return to_string(x); }
static string _json(unsigned x) { return to_string(x); }
static string _json(size_t x) { return to_string(x); }
static string _json(double x) { ostringstream o; o << setprecision(10) << x; return o.str(); }
static string _json(bool x) { return x ? "true" : "false"; }
static string _json(const string& s) {
    string o = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += c; }
        else if (c == '\n') o += "\\n";
        else if (c < 0x20) { char b[8]; snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += c;
    }
    return o + "\"";
}
static string _json(const char* s) { return _json(string(s)); }
static string _json(char c) { return _json(string(1, c)); }
static string _json(ListNode* h) {
    string o = "["; int n = 0;
    for (; h && n < 10000; h = h->next, n++) o += (n ? "," : "") + to_string(h->val);
    return o + "]";
}
static string _json(TreeNode* r) {
    vector<string> out; queue<TreeNode*> q; q.push(r);
    while (!q.empty() && out.size() < 20000) {
        TreeNode* n = q.front(); q.pop();
        if (!n) { out.push_back("null"); continue; }
        out.push_back(to_string(n->val)); q.push(n->left); q.push(n->right);
    }
    while (!out.empty() && out.back() == "null") out.pop_back();
    string o = "[";
    for (size_t i = 0; i < out.size(); i++) o += (i ? "," : "") + out[i];
    return o + "]";
}
template <class T> static string _json(const vector<T>& v) {
    string o = "[";
    for (size_t i = 0; i < v.size(); i++) { if (i) o += ","; o += _json((T)v[i]); }
    return o + "]";
}
static void _emit_raw(const string& s) { cout.flush(); cout << "\n@@CODELENS_RESULT@@\n" << s << "\n"; cout.flush(); }
template <class T> static void _emit(const T& x) { _emit_raw(_json(x)); }
'''

# macOS clang has no <bits/stdc++.h>; LeetCode code often includes it.
BITS_STDCPP = """#pragma once
#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <functional>
#include <iomanip>
#include <iostream>
#include <list>
#include <map>
#include <numeric>
#include <optional>
#include <queue>
#include <set>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
"""
