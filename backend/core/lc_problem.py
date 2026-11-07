"""LeetCode problem lookup: bundled offline catalog first, then LeetCode's public
GraphQL API (cached on disk so each problem is fetched once).

Accepts a frontend id ("1"), a slug ("two-sum"), a title ("Two Sum") or a URL.
"""

import html
import json
import re
from functools import lru_cache
from pathlib import Path

import httpx

from api.schemas.leetcode import LCExample, LCMethod, LCParam, LCProblem, LCSummary
from core.lc_cpp import cpp_starter
from core.lc_runtime import TestInputError

_CATALOG_PATH = Path(__file__).parent.parent / "models" / "leetcode_catalog.json"
_GRAPHQL = "https://leetcode.com/graphql"
_HEADERS = {"Referer": "https://leetcode.com", "Content-Type": "application/json", "User-Agent": "CodeLens/1.0"}

_Q_DETAIL = """query q($slug: String!) { question(titleSlug: $slug) {
  questionFrontendId title titleSlug difficulty isPaidOnly content exampleTestcaseList metaData
  topicTags { name } codeSnippets { langSlug code } } }"""
_Q_SEARCH_FULL = """query q($kw: String, $limit: Int) { problemsetQuestionList: questionList(categorySlug: "",
  limit: $limit, skip: 0, filters: {searchKeywords: $kw}) { questions: data {
  questionFrontendId title titleSlug difficulty paidOnly: isPaidOnly } } }"""
_Q_SEARCH = """query q($kw: String) { problemsetQuestionList: questionList(categorySlug: "", limit: 50,
  skip: 0, filters: {searchKeywords: $kw}) { questions: data { questionFrontendId titleSlug } } }"""


class ProblemNotFoundError(LookupError):
    """No problem matches the reference, or it cannot be fetched."""


# ----------------------------------------------------------------- catalog ----
@lru_cache
def catalog() -> dict[str, LCProblem]:
    """Bundled problems keyed by both id and slug."""
    problems = [LCProblem.model_validate(p) for p in json.loads(_CATALOG_PATH.read_text())]
    out: dict[str, LCProblem] = {}
    for p in problems:
        p = p.model_copy(update={"starter_code": p.starter_code or starter_code(p),
                                 "starter_code_cpp": safe_cpp_starter(p),
                                 "url": f"https://leetcode.com/problems/{p.slug}/"})
        out[p.id] = out[p.slug] = p
    return out


def catalog_summaries() -> list[LCSummary]:
    seen = {p.slug: p for p in catalog().values()}
    return sorted((LCSummary(id=p.id, slug=p.slug, title=p.title, difficulty=p.difficulty)
                   for p in seen.values()), key=lambda s: int(s.id))


def search_catalog(query: str, limit: int = 8) -> list[LCSummary]:
    """Bundled problems whose number, title or slug matches `query`."""
    q = query.strip().lower()
    hits = [s for s in catalog_summaries()
            if q and (s.id.startswith(q) or q in s.title.lower() or q in s.slug)]
    return sorted(hits, key=lambda s: (s.id != q, not s.title.lower().startswith(q), int(s.id)))[:limit]


def normalize_ref(ref: str) -> str:
    """'1' → '1'; URL or title → slug."""
    ref = ref.strip()
    if m := re.search(r"leetcode\.(?:com|cn)/problems/([\w-]+)", ref):
        return m.group(1).lower()
    if ref.isdigit():
        return str(int(ref))
    return re.sub(r"[^a-z0-9]+", "-", ref.lower()).strip("-")


# ------------------------------------------------------------ starter code ----
_PY_TYPES = {
    "integer": "int", "long": "int", "double": "float", "boolean": "bool", "string": "str",
    "character": "str", "void": "None", "ListNode": "Optional[ListNode]", "TreeNode": "Optional[TreeNode]",
}


def py_type(lc_type: str) -> str:
    """LeetCode type → Python annotation ("integer[][]" → "List[List[int]]")."""
    lc_type = re.sub(r"^list<(.+)>$", r"\1[]", lc_type)
    depth = 0
    while lc_type.endswith("[]"):
        lc_type, depth = lc_type[:-2], depth + 1
    base = _PY_TYPES.get(lc_type, "Any")
    if depth and base.startswith("Optional["):
        base = base[9:-1]
    for _ in range(depth):
        base = f"List[{base}]"
    return base


_LISTNODE_DOC = (
    "# Definition for singly-linked list.\n# class ListNode:\n#     def __init__(self, val=0, next=None):\n"
    "#         self.val = val\n#         self.next = next\n"
)
_TREENODE_DOC = (
    "# Definition for a binary tree node.\n# class TreeNode:\n#     def __init__(self, val=0, left=None, right=None):\n"
    "#         self.val = val\n#         self.left = left\n#         self.right = right\n"
)


def _sig(name: str, params: list[LCParam], ret: str) -> str:
    args = "".join(f", {p.name}: {py_type(p.type)}" for p in params)
    return f"    def {name}(self{args}) -> {py_type(ret)}:\n        pass\n"


def starter_code(p: LCProblem) -> str:
    """Python 3 skeleton in LeetCode's style."""
    header = ""
    types = " ".join(x.type for x in [*p.params, *p.constructor_params]) + p.return_type
    if "ListNode" in types:
        header += _LISTNODE_DOC
    if "TreeNode" in types:
        header += _TREENODE_DOC
    if p.design:
        body = _sig("__init__", p.constructor_params, "void").replace(" -> None", "")
        body += "".join("\n" + _sig(m.name, m.params, m.return_type) for m in p.methods)
        return f"{header}{chr(10) if header else ''}class {p.class_name}:\n\n{body}"
    sep = "\n" if header else ""
    return f"{header}{sep}class Solution:\n{_sig(p.function_name or 'solve', p.params, p.return_type)}"


# -------------------------------------------------------------- HTML → text ----
def html_to_text(content: str) -> str:
    """Readable plain text from LeetCode's problem HTML (no markup reaches the UI)."""
    text = re.sub(r"<sup>(.*?)</sup>", r"^\1", content, flags=re.S)
    text = re.sub(r"<li>\s*", "\n• ", text)
    text = re.sub(r"</?(p|div|pre|ul|ol|br|li)[^>]*>", "\n", text)
    text = re.sub(r"<img[^>]*>", "[image]", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_example_outputs(text: str) -> list[str]:
    """`Output: [0,1]` values in order of appearance."""
    return [m.strip() for m in re.findall(r"^\s*Output:?\s*(.+?)\s*$", text, flags=re.M)]


def _strip_examples(text: str) -> str:
    """Statement + constraints; the examples become runnable test cases instead."""
    m = re.search(r"Example 1:?.*?(?=Constraints:|Follow[- ]?up|$)", text, flags=re.S)
    return (text[: m.start()] + text[m.end():]).strip() if m else text


# --------------------------------------------------------------- live fetch ----
def from_graphql(q: dict) -> LCProblem:
    """Build an LCProblem from a GraphQL `question` object."""
    if q.get("isPaidOnly") or not q.get("content"):
        raise ProblemNotFoundError(f"“{q.get('title')}” is a premium problem — its statement isn't public.")
    meta = json.loads(q.get("metaData") or "{}")
    text = html_to_text(q["content"])
    outputs = parse_example_outputs(text)
    inputs = [case.split("\n") for case in q.get("exampleTestcaseList") or []]
    examples = [LCExample(input=inp, expected=outputs[i] if i < len(outputs) else None)
                for i, inp in enumerate(inputs)]
    design = bool(meta.get("systemdesign") or meta.get("classname"))
    params = [LCParam(name=p["name"], type=p["type"]) for p in meta.get("params", [])]
    problem = LCProblem(
        id=str(q["questionFrontendId"]), slug=q["titleSlug"], title=q["title"],
        difficulty=q.get("difficulty", ""), tags=[t["name"] for t in q.get("topicTags") or []],
        description=_strip_examples(text),
        function_name=meta.get("name"), params=params,
        return_type=(meta.get("return") or {}).get("type", "void"),
        output_param=(meta.get("output") or {}).get("paramindex"),
        design=design, class_name=meta.get("classname"),
        constructor_params=[LCParam(**p) for p in (meta.get("constructor") or {}).get("params", [])],
        methods=[LCMethod(name=m["name"], params=[LCParam(**p) for p in m.get("params", [])],
                          return_type=(m.get("return") or {}).get("type", "void"))
                 for m in meta.get("methods", [])],
        examples=examples, source="leetcode", url=f"https://leetcode.com/problems/{q['titleSlug']}/",
    )
    snippets = {s["langSlug"]: s["code"] for s in q.get("codeSnippets") or []}
    return problem.model_copy(update={
        "starter_code": snippets.get("python3") or starter_code(problem),
        "starter_code_cpp": snippets.get("cpp") or safe_cpp_starter(problem),
    })


def safe_cpp_starter(p: LCProblem) -> str:
    try:
        return cpp_starter(p)
    except TestInputError:
        return ""


class LeetCodeClient:
    """Fetches problems from leetcode.com with an on-disk JSON cache."""

    def __init__(self, http: httpx.AsyncClient, cache_dir: Path) -> None:
        self.http, self.cache_dir = http, cache_dir

    async def _gql(self, query: str, variables: dict) -> dict:
        try:
            res = await self.http.post(_GRAPHQL, json={"query": query, "variables": variables},
                                       headers=_HEADERS, timeout=15)
        except httpx.HTTPError as exc:
            raise ProblemNotFoundError("Couldn't reach leetcode.com — check your internet connection.") from exc
        if res.status_code != 200:
            raise ProblemNotFoundError(f"leetcode.com returned HTTP {res.status_code}.")
        return res.json().get("data") or {}

    async def search(self, query: str, limit: int = 8) -> list[LCSummary]:
        """Live LeetCode search by number or keywords (premium problems excluded)."""
        data = await self._gql(_Q_SEARCH_FULL, {"kw": query.strip(), "limit": limit})
        questions = (data.get("problemsetQuestionList") or {}).get("questions") or []
        return [LCSummary(id=str(q["questionFrontendId"]), slug=q["titleSlug"], title=q["title"],
                          difficulty=q.get("difficulty", "")) for q in questions if not q.get("paidOnly")]

    async def _slug_for_id(self, frontend_id: str) -> str:
        data = await self._gql(_Q_SEARCH, {"kw": frontend_id})
        for q in (data.get("problemsetQuestionList") or {}).get("questions") or []:
            if str(q["questionFrontendId"]) == frontend_id:
                return q["titleSlug"]
        raise ProblemNotFoundError(f"No LeetCode problem #{frontend_id}.")

    async def get(self, ref: str) -> LCProblem:
        key = normalize_ref(ref)
        if not key:
            raise ProblemNotFoundError("Enter a problem number, slug or URL.")
        if key in catalog():
            return catalog()[key]
        index = self.cache_dir / "index.json"
        ids = json.loads(index.read_text()) if index.exists() else {}
        slug = ids.get(key) or (await self._slug_for_id(key) if key.isdigit() else key)
        cached = self.cache_dir / f"{slug}.json"
        if cached.exists():
            problem = LCProblem.model_validate_json(cached.read_text())
            if problem.starter_code_cpp:
                return problem
            # cached by an older version (no C++ starter): refresh, or derive one offline
            try:
                data = await self._gql(_Q_DETAIL, {"slug": slug})
            except ProblemNotFoundError:
                return problem.model_copy(update={"starter_code_cpp": safe_cpp_starter(problem)})
        else:
            data = await self._gql(_Q_DETAIL, {"slug": slug})
        if not data.get("question"):
            raise ProblemNotFoundError(f"No LeetCode problem called “{ref}”.")
        problem = from_graphql(data["question"])
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(problem.model_dump_json())
        index.write_text(json.dumps({**ids, problem.id: problem.slug}))
        return problem
