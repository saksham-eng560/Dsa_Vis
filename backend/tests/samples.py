"""Algorithm samples shared by tests: name -> (code, best, worst, space)."""

CASES = {
    'bubble': ('def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        swapped = False\n        for j in range(n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n                swapped = True\n        if not swapped:\n            break\n    return arr\n', 'O(n)', 'O(n²)', 'O(1)'),
    'binsearch': ('def binary_search(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n', 'O(1)', 'O(log n)', 'O(1)'),
    'fib': ('def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n', 'O(2ⁿ)', 'O(2ⁿ)', 'O(n)'),
    'fibmemo': ('from functools import lru_cache\n@lru_cache(None)\ndef fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n', 'O(n)', 'O(n)', 'O(n)'),
    'merge': ('def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    return merge(left, right)\n\ndef merge(a, b):\n    out = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] < b[j]:\n            out.append(a[i]); i += 1\n        else:\n            out.append(b[j]); j += 1\n    return out + a[i:] + b[j:]\n', 'O(n log n)', 'O(n log n)', 'O(n)'),
    'quick': ('def partition(arr, low, high):\n    pivot = arr[high]\n    i = low - 1\n    for j in range(low, high):\n        if arr[j] <= pivot:\n            i += 1\n            arr[i], arr[j] = arr[j], arr[i]\n    arr[i + 1], arr[high] = arr[high], arr[i + 1]\n    return i + 1\n\ndef quick_sort(arr, low, high):\n    if low < high:\n        pi = partition(arr, low, high)\n        quick_sort(arr, low, pi - 1)\n        quick_sort(arr, pi + 1, high)\n', 'O(n²)', 'O(n²)', 'O(log n)'),
    'twosum': ('def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i\n', 'O(1)', 'O(n)', 'O(n)'),
    'bfs': ('from collections import deque\ndef bfs(graph, start):\n    visited = {start}\n    queue = deque([start])\n    order = []\n    while queue:\n        node = queue.popleft()\n        order.append(node)\n        for nb in graph[node]:\n            if nb not in visited:\n                visited.add(nb)\n                queue.append(nb)\n    return order\n', 'O(V + E)', 'O(V + E)', 'O(V)'),
    'perm': ('def permute(nums):\n    res = []\n    def bt(path, rest):\n        if not rest:\n            res.append(path[:]); return\n        for i in range(len(rest)):\n            bt(path + [rest[i]], rest[:i] + rest[i+1:])\n    bt([], nums)\n    return res\n', 'O(n!)', 'O(n!)', 'O(n)'),
}

C_CASES = {
    "js_bubble": ('function bubbleSort(arr) {\n  for (let i = 0; i < arr.length; i++) {\n    for (let j = 0; j < arr.length - i - 1; j++) {\n      if (arr[j] > arr[j + 1]) {\n        [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];\n      }\n    }\n  }\n  return arr;\n}\nconsole.log(bubbleSort([5, 3, 1]));', "O(n²)"),
    "cpp_mixed": ('#include <vector>\nint binarySearch(std::vector<int>& a, int t) {\n    int lo = 0, hi = a.size() - 1;\n    while (lo <= hi) {\n        int mid = lo + (hi - lo) / 2;\n        if (a[mid] == t) return mid;\n        else if (a[mid] < t) lo = mid + 1;\n        else hi = mid - 1;\n    }\n    return -1;\n}\nint fib(int n) { if (n < 2) return n; return fib(n-1) + fib(n-2); }', "O(2ⁿ)"),
}

# Regression cases found via the UI walkthrough.
CASES["bst_insert"] = (
    "def insert(root, val):\n    if root is None:\n        return Node(val)\n    if val < root.val:\n"
    "        root.left = insert(root.left, val)\n    else:\n        root.right = insert(root.right, val)\n"
    "    return root\n",
    "O(1)", "O(n)", "O(n)",
)
CASES["inorder"] = (
    "def inorder(node, out):\n    if node:\n        inorder(node.left, out)\n        out.append(node.val)\n"
    "        inorder(node.right, out)\n",
    "O(n)", "O(n)", "O(n)",
)
CASES["dfs_recursive"] = (
    "def dfs(graph, node, visited):\n    visited.add(node)\n    for nb in graph[node]:\n"
    "        if nb not in visited:\n            dfs(graph, nb, visited)\n",
    "O(V + E)", "O(V + E)", "O(V)",
)
C_CASES["js_quicksort"] = (
    "function quickSort(arr, lo, hi) {\n  if (lo < hi) {\n    const p = partition(arr, lo, hi);\n"
    "    quickSort(arr, lo, p - 1);\n    quickSort(arr, p + 1, hi);\n  }\n  return arr;\n}\n"
    "function partition(arr, lo, hi) {\n  let i = lo - 1;\n  for (let j = lo; j < hi; j++) { i++; }\n  return i + 1;\n}\n",
    "O(n²)",
)
C_CASES["cpp_dfs"] = (
    "void dfs(int node, vector<vector<int>>& adj, vector<bool>& visited) {\n    visited[node] = true;\n"
    "    for (int next : adj[node]) {\n        if (!visited[next]) {\n            dfs(next, adj, visited);\n"
    "        }\n    }\n}\n",
    "O(V + E)",
)
CASES["min_stack_methods"] = (
    "class MinStack:\n    def __init__(self):\n        self.stack = []\n        self.mins = []\n"
    "    def pop(self):\n        self.stack.pop()\n        self.mins.pop()\n"
    "    def top(self):\n        return self.stack[-1]\n",
    "O(1)", "O(1)", "O(1)",
)
