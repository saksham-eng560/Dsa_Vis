"""Pydantic response models — the single source of truth for the API contract.

The frontend mirrors these in `frontend/src/types/index.ts`. LLM output is
validated against the same models, so malformed fields are rejected at the edge.
"""

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field

NodeType = Literal["start", "process", "decision", "io", "end"]
DSType = Literal[
    "array", "matrix", "stack", "queue", "linked_list", "tree", "graph", "hash_map", "heap"
]
Source = Literal["llm", "static", "trace", "none"]


class FlowNode(BaseModel):
    """One flowchart node. `group` is the owning function (or "<program>" for top level)."""

    id: str
    type: NodeType = "process"
    label: str
    line: int | None = None
    end_line: int | None = None
    group: str = "<program>"


class FlowEdge(BaseModel):
    """Directed flowchart edge; accepts the LLM's `from`/`to` spelling too."""

    source: str = Field(validation_alias=AliasChoices("source", "from"))
    target: str = Field(validation_alias=AliasChoices("target", "to"))
    label: str | None = None


class Flowchart(BaseModel):
    nodes: list[FlowNode] = Field(default_factory=list)
    edges: list[FlowEdge] = Field(default_factory=list)
    source: Source = "none"


class TimeComplexity(BaseModel):
    best: str = "O(?)"
    average: str = "O(?)"
    worst: str = "O(?)"
    explanation: str = ""


class SpaceComplexity(BaseModel):
    complexity: str = "O(?)"
    explanation: str = ""


class Complexity(BaseModel):
    time: TimeComplexity = Field(default_factory=TimeComplexity)
    space: SpaceComplexity = Field(default_factory=SpaceComplexity)
    source: Source = "none"


class Highlight(BaseModel):
    """Marks an index (array), node id (tree/graph/list), key (map) or [r, c] cell."""

    target: Any = Field(validation_alias=AliasChoices("target", "index_or_node"))
    color: Literal["green", "red", "yellow", "blue", "purple"] = "yellow"
    label: str = ""


class DataStructureState(BaseModel):
    """Snapshot of the focused data structure. `state` shape depends on `type`:

    array/stack/queue/heap: {"values": [...]}
    matrix: {"rows": [[...]]}
    hash_map: {"entries": [[key, value], ...]}
    linked_list: {"nodes": [{"id", "value"}], "cycle_to": id | None}
    tree: {"root": {"id", "value", "children": [node | None, ...]} | None}
    graph: {"nodes": [{"id", "label"}], "edges": [{"source", "target", "weight"}], "directed": bool}
    """

    type: DSType
    name: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    highlights: list[Highlight] = Field(default_factory=list)
    caption: str = ""  # e.g. "dp[i] = number of ways to reach stair i" (from the visual plan)


class DryRunStep(BaseModel):
    step: int
    line: int | None = None
    event: Literal["line", "call", "return", "exception"] = "line"
    function: str = "<module>"
    depth: int = 0
    description: str = ""
    variables: dict[str, str] = Field(default_factory=dict)
    changed: list[str] = Field(default_factory=list)
    data_structure_state: DataStructureState | None = None  # primary view (first of data_structures)
    data_structures: list[DataStructureState] = Field(default_factory=list)  # every tracked structure
    output_so_far: str = ""


class CallNode(BaseModel):
    """One function call in the recursion tree (step indices are 0-based into DryRun.steps)."""

    id: int
    parent: int | None = None
    func: str
    args: str = ""
    ret: str | None = None
    start: int
    end: int | None = None  # step index of the return (None: never returned / truncated)
    repeat: int = 0  # how many identical calls (same function + args) happened before this one
    cached: bool = False  # repeat answered without recursing (memo / cache hit)


class CallTree(BaseModel):
    nodes: list[CallNode] = Field(default_factory=list)
    recursive: bool = False  # some function calls itself (directly or indirectly)
    repeated: int = 0  # calls that recomputed an already-seen subproblem
    cache_hits: int = 0  # repeats answered from a memo/cache without recursing
    truncated: bool = False


class VisualPlan(BaseModel):
    """What the AI decided to show for this problem/solution (declarative, safe to apply)."""

    focus: list[str] = Field(default_factory=list)  # variable names in display order
    captions: dict[str, str] = Field(default_factory=dict)
    show_recursion_tree: bool | None = None
    insight: str = ""  # one-line "what to watch" hint shown above the visuals


class DryRun(BaseModel):
    input_example: str = ""
    steps: list[DryRunStep] = Field(default_factory=list)
    call_tree: CallTree | None = None
    plan: VisualPlan | None = None
    source: Source = "none"
    truncated: bool = False
    error: str | None = None


class KeyConcept(BaseModel):
    concept: str
    explanation: str = ""
    relevance: str = ""


class AnalysisResult(BaseModel):
    """Full output of the analysis pipeline."""

    language: str
    summary: str = ""
    intuition: str = ""
    approach: list[str] = Field(default_factory=list)  # "Line N: …" steps
    why_it_works: str = ""
    common_mistakes: list[str] = Field(default_factory=list)
    algorithm_name: str = "Custom Logic"
    data_structures_used: list[str] = Field(default_factory=list)
    complexity: Complexity = Field(default_factory=Complexity)
    flowchart: Flowchart = Field(default_factory=Flowchart)
    dry_run: DryRun = Field(default_factory=DryRun)
    key_concepts: list[KeyConcept] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    optimizations: list[str] = Field(default_factory=list)
    related_algorithms: list[str] = Field(default_factory=list)
    llm_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class Explanation(BaseModel):
    """Output of `/api/explain` (subset of AnalysisResult, optionally ELI5)."""

    summary: str = ""
    intuition: str = ""
    approach: list[str] = Field(default_factory=list)  # "Line N: …" steps
    why_it_works: str = ""
    common_mistakes: list[str] = Field(default_factory=list)
    algorithm_name: str = "Custom Logic"
    key_concepts: list[KeyConcept] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    optimizations: list[str] = Field(default_factory=list)
    related_algorithms: list[str] = Field(default_factory=list)
    eli5: bool = False
    llm_used: bool = False


class HealthStatus(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    llm_provider: str
    llm_model: str | None
    llm_available: bool
