"""Shared mutable graph builder used by the Python and C-family flowchart walkers."""

from api.schemas.response import FlowEdge, FlowNode, NodeType

# A dangling edge waiting for its target: (source node id, edge label).
Pending = tuple[str, str | None]

# Group name for top-level (module / script) code — distinct from a function named `main`.
PROGRAM_GROUP = "<program>"


class FlowBuilder:
    """Accumulates nodes/edges with sequential ids (n1, n2, …)."""

    def __init__(self) -> None:
        self.nodes: list[FlowNode] = []
        self.edges: list[FlowEdge] = []

    def node(
        self,
        kind: NodeType,
        label: str,
        group: str,
        line: int | None,
        end_line: int | None = None,
    ) -> str:
        """Add a node and return its id."""
        nid = f"n{len(self.nodes) + 1}"
        self.nodes.append(
            FlowNode(id=nid, type=kind, label=label, line=line, end_line=end_line or line, group=group)
        )
        return nid

    def connect(self, preds: list[Pending], target: str, label: str | None = None) -> None:
        """Wire every pending exit to `target` (pending labels win over `label`)."""
        for source, edge_label in preds:
            self.edges.append(FlowEdge(source=source, target=target, label=edge_label or label))
