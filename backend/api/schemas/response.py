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


class DryRunStep(BaseModel):
    step: int
    line: int | None = None
    event: Literal["line", "call", "return", "exception"] = "line"
    function: str = "<module>"
    depth: int = 0
    description: str = ""
    variables: dict[str, str] = Field(default_factory=dict)
    changed: list[str] = Field(default_factory=list)
    data_structure_state: DataStructureState | None = None
    output_so_far: str = ""


class DryRun(BaseModel):
    input_example: str = ""
    steps: list[DryRunStep] = Field(default_factory=list)
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
