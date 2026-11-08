"""Real sandboxed execution traces → data-structure snapshots."""

import sys

import pytest

from core.tracer import trace_python


async def run(code: str, entry: str | None = None, steps: int = 400, timeout: float = 3):
    return await trace_python(code, entry, max_steps=steps, timeout_s=timeout, memory_mb=256)


async def test_array_pointers_and_swaps() -> None:
    code = (
        "def bubble(arr):\n"
        "    for i in range(len(arr)):\n"
        "        for j in range(len(arr) - i - 1):\n"
        "            if arr[j] > arr[j + 1]:\n"
        "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
        "    return arr\n"
    )
    run_ = await run(code, "bubble([3, 1, 2])")
    assert run_.error is None and run_.source == "trace"
    states = [s.data_structure_state for s in run_.steps if s.data_structure_state]
    assert states[0].type == "array" and states[0].name == "arr"
    assert states[-1].state["values"] == [1, 2, 3]
    labels = {h.label for s in states for h in s.highlights}
    assert {"i", "j", "changed"} <= labels
    assert "bubble([3, 1, 2]) = [1, 2, 3]" in run_.steps[-1].output_so_far


async def test_linked_list_with_pointer_highlights() -> None:
    code = (
        "class Node:\n"
        "    def __init__(self, val, next=None):\n"
        "        self.val = val\n"
        "        self.next = next\n"
        "head = Node(1, Node(2, Node(3)))\n"
        "prev, curr = None, head\n"
        "while curr:\n"
        "    nxt = curr.next\n"
        "    curr.next = prev\n"
        "    prev, curr = curr, nxt\n"
    )
    run_ = await run(code)
    states = [s.data_structure_state for s in run_.steps if s.data_structure_state]
    assert all(s.type == "linked_list" for s in states)
    assert [n["value"] for n in states[0].state["nodes"]] == [1, 2, 3]
    assert any(h.label == "curr" for s in states for h in s.highlights)


async def test_tree_detection() -> None:
    code = (
        "class T:\n"
        "    def __init__(self, v, left=None, right=None):\n"
        "        self.val, self.left, self.right = v, left, right\n"
        "def inorder(node, out):\n"
        "    if node:\n"
        "        inorder(node.left, out)\n"
        "        out.append(node.val)\n"
        "        inorder(node.right, out)\n"
        "root = T(2, T(1), T(3))\n"
        "res = []\n"
        "inorder(root, res)\n"
    )
    run_ = await run(code)
    tree = next(s.data_structure_state for s in run_.steps
                if s.data_structure_state and s.data_structure_state.type == "tree")
    assert tree.state["root"]["value"] == 2
    assert [c["value"] for c in tree.state["root"]["children"]] == [1, 3]


async def test_graph_bfs_marks_visited() -> None:
    code = (
        "from collections import deque\n"
        "graph = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}\n"
        "visited = {'A'}\n"
        "queue = deque(['A'])\n"
        "while queue:\n"
        "    node = queue.popleft()\n"
        "    for nb in graph[node]:\n"
        "        if nb not in visited:\n"
        "            visited.add(nb)\n"
        "            queue.append(nb)\n"
    )
    run_ = await run(code)
    last = run_.steps[-1].data_structure_state
    assert last is not None and last.type == "graph" and last.state["directed"] is True
    assert {h.target for h in last.highlights if h.label == "visited"} == {"A", "B", "C", "D"}


async def test_runtime_error_is_reported() -> None:
    run_ = await run("x = [1]\nprint(x[5])\n")
    assert run_.error and run_.error.startswith("IndexError")


async def test_sandbox_blocks_dangerous_operations() -> None:
    for code in (
        "import socket",
        "import subprocess",
        "open('/tmp/codelens_pwned', 'w')",
        "import os\nos.system('true')",
        "import os\nos.remove('/etc/hostname')",
    ):
        run_ = await run(code)
        assert run_.error and "PermissionError" in run_.error, code


async def test_infinite_loop_is_bounded() -> None:
    run_ = await run("x = 0\nwhile True:\n    x += 1\n", steps=50)
    assert run_.truncated and len(run_.steps) == 50


async def test_timeout_without_traced_lines() -> None:
    run_ = await run("while True: pass\n" * 1, steps=10_000_000, timeout=1)
    assert run_.error and "timed out" in run_.error


@pytest.mark.skipif(sys.platform == "darwin", reason="macOS does not enforce RLIMIT_AS")
async def test_memory_bomb_is_contained() -> None:
    run_ = await run("x = ' ' * (1024 ** 3)\n")
    assert run_.error and "MemoryError" in run_.error


async def test_tree_focus_prefers_whole_global_tree() -> None:
    code = (
        "class N:\n"
        "    def __init__(self, v):\n"
        "        self.val, self.left, self.right = v, None, None\n"
        "def insert(root, v):\n"
        "    if root is None:\n"
        "        return N(v)\n"
        "    if v < root.val:\n"
        "        root.left = insert(root.left, v)\n"
        "    else:\n"
        "        root.right = insert(root.right, v)\n"
        "    return root\n"
        "root = None\n"
        "for v in [5, 3, 8, 1]:\n"
        "    root = insert(root, v)\n"
    )
    run_ = await run(code)
    inside = [s for s in run_.steps if s.function == "insert" and s.depth >= 2 and s.data_structure_state]
    assert inside, "expected recursive insert steps"
    for s in inside:
        assert s.data_structure_state.state["root"]["value"] == 5  # whole tree, not the subtree
    assert any(h.label == "root" for s in inside for h in s.data_structure_state.highlights)
