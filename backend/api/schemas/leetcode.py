"""Schemas for LeetCode problem mode (mirrored in frontend/src/types/leetcode.ts)."""

from typing import Literal

from pydantic import BaseModel, Field

CompareMode = Literal["exact", "unordered", "unordered_nested"]
TestStatus = Literal["passed", "failed", "error", "timeout", "ran"]
SolutionLanguage = Literal["python", "cpp"]


class LCParam(BaseModel):
    name: str
    type: str  # LeetCode type, e.g. "integer[]", "TreeNode", "character[][]"


class LCMethod(BaseModel):
    """A method of a design problem (e.g. LRUCache.get)."""

    name: str
    params: list[LCParam] = Field(default_factory=list)
    return_type: str = "void"


class LCExample(BaseModel):
    input: list[str]  # one LeetCode-format value per line
    expected: str | None = None


class LCSummary(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: str


class LCProblem(LCSummary):
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    function_name: str | None = None
    params: list[LCParam] = Field(default_factory=list)
    return_type: str = "void"
    output_param: int | None = None  # in-place problems judge this argument
    design: bool = False
    class_name: str | None = None
    constructor_params: list[LCParam] = Field(default_factory=list)
    methods: list[LCMethod] = Field(default_factory=list)
    starter_code: str = ""  # Python 3
    starter_code_cpp: str = ""  # C++ ("" when a type is unsupported)
    examples: list[LCExample] = Field(default_factory=list)
    compare: CompareMode = "exact"
    source: Literal["bundled", "leetcode"] = "bundled"
    url: str = ""


class LCTestCase(BaseModel):
    input: list[str] = Field(max_length=20)
    expected: str | None = Field(default=None, max_length=20_000)


class RunTestsRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100_000)
    problem: str = Field(min_length=1, max_length=200)
    tests: list[LCTestCase] = Field(min_length=1, max_length=30)
    compare: CompareMode | None = None  # default: the problem's own mode
    language: SolutionLanguage = "python"


class TestResult(BaseModel):
    status: TestStatus
    label: str = ""
    output: str | None = None  # JSON text of the returned value
    expected: str | None = None
    error: str | None = None
    stdout: str = ""
    ms: float = 0.0


class RunTestsResponse(BaseModel):
    results: list[TestResult]
    passed: int
    total: int
    compare: CompareMode
    error: str | None = None  # fatal: syntax error, missing Solution, …
