"""Remember every linked node (list/tree) seen during a trace, by stable id.

Snapshots only contain what is reachable from in-scope variables. Inside a
recursive helper that may be just a subtree; while reversing a list, `head`
reaches a single node. The registry keeps the freshest fields of every node
ever seen so the visualiser can always draw the *whole* structure.
"""

from core.value_model import Value, node_value, tag

_MAX_NODES = 400


class NodeRegistry:
    def __init__(self) -> None:
        self.fields: dict[int, dict[str, Value]] = {}
        self.cls: dict[int, str] = {}
        self.order: list[int] = []  # fixed left-to-right positions for list nodes

    def update(self, value: Value) -> None:
        """Record fresh fields for every object node reachable in `value`."""
        stack = [value]
        while stack:
            v = stack.pop()
            t = tag(v)
            if t == "obj" and len(self.fields) < _MAX_NODES:
                self.fields[v["id"]] = v["f"]
                self.cls[v["id"]] = v.get("cls", "")
                stack.extend(v["f"].values())
            elif t in ("list", "tuple", "set", "deque"):
                stack.extend(v["v"])
            elif t == "dict":
                stack.extend(x for pair in v["v"] for x in pair)

    def _ref_id(self, v: Value) -> int | None:
        return v["id"] if tag(v) in ("obj", "ref") else None

    def whole(self, kind: str, root_id: int) -> Value:
        """Rebuild the structure rooted at `root_id` as a tagged object (refs for revisits)."""
        seen: set[int] = set()

        def build(node_id: int | None) -> Value:
            if node_id is None or node_id not in self.fields:
                return None
            if node_id in seen or len(seen) > _MAX_NODES:
                return {"t": "ref", "id": node_id}
            seen.add(node_id)
            f = self.fields[node_id]
            out: dict[str, Value] = {k: v for k, v in f.items() if tag(v) not in ("obj", "ref")}
            for key in ("next", "left", "right"):
                if key in f:
                    out[key] = build(self._ref_id(f[key]))
            if "children" in f and tag(f["children"]) in ("list", "tuple"):
                out["children"] = {"t": "list", "v": [build(self._ref_id(c)) for c in f["children"]["v"]]}
            return {"t": "obj", "cls": self.cls.get(node_id, ""), "id": node_id, "f": out}

        return build(root_id)

    def list_ids(self, root_id: int | None) -> list[int]:
        """List nodes in stable display order: first seen along `next` from the root, then the rest."""
        known = set(self.order)
        starts = ([root_id] if root_id is not None else []) + sorted(self.fields)
        for start in starts:
            node: int | None = start
            while node is not None and node in self.fields and "next" in self.fields[node] and node not in known:
                self.order.append(node)
                known.add(node)
                node = self._ref_id(self.fields[node].get("next"))
        return list(self.order)

    def all_lists(self, root_id: int | None) -> Value:
        """Every known list node as one value (used to match pointer variables to nodes)."""
        return {"t": "list", "v": [{"t": "obj", "cls": "", "id": i, "f": {}} for i in self.list_ids(root_id)]}

    def list_state(self, root_id: int | None = None) -> dict:
        """Every list node ever seen, at a fixed position, with its *current* `next` arrow."""
        ids = self.list_ids(root_id)
        nodes = [{"id": str(i), "value": node_value(self.fields[i])} for i in ids]
        edges = []
        for i in ids:
            nxt = self._ref_id(self.fields[i].get("next"))
            if nxt is not None and nxt in self.fields:
                edges.append({"source": str(i), "target": str(nxt)})
        return {"nodes": nodes, "edges": edges, "cycle_to": None}
