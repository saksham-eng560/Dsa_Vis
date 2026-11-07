/** Example snippets for quick demos — chosen to exercise every visualiser. */
import type { Language } from '../types';

export interface Preset {
  id: string;
  title: string;
  language: Language;
  code: string;
  entryCall?: string;
}

export const PRESETS: Preset[] = [
  {
    id: 'bubble',
    title: 'Bubble Sort · array',
    language: 'python',
    code: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


print(bubble_sort([5, 1, 4, 2, 8]))
`,
  },
  {
    id: 'binary-search',
    title: 'Binary Search · pointers',
    language: 'python',
    code: `def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


print(binary_search([1, 3, 5, 7, 9, 11, 13, 15], 11))
`,
  },
  {
    id: 'bfs',
    title: 'BFS · graph',
    language: 'python',
    code: `from collections import deque


def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in graph[node]:
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)
    return order


graph = {"A": ["B", "C"], "B": ["D", "E"], "C": ["F"], "D": [], "E": ["F"], "F": []}
print(bfs(graph, "A"))
`,
  },
  {
    id: 'reverse-list',
    title: 'Reverse Linked List',
    language: 'python',
    code: `class Node:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next


def reverse(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev


head = Node(1, Node(2, Node(3, Node(4))))
head = reverse(head)
`,
  },
  {
    id: 'bst',
    title: 'BST Insert + Inorder · tree',
    language: 'python',
    code: `class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None


def insert(root, val):
    if root is None:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    else:
        root.right = insert(root.right, val)
    return root


def inorder(node, out):
    if node:
        inorder(node.left, out)
        out.append(node.val)
        inorder(node.right, out)


root = None
for v in [8, 3, 10, 1, 6, 14]:
    root = insert(root, v)
result = []
inorder(root, result)
print(result)
`,
  },
  {
    id: 'stack',
    title: 'Valid Parentheses · stack',
    language: 'python',
    code: `def is_valid(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        else:
            stack.append(ch)
    return not stack


print(is_valid("({[]})"))
`,
  },
  {
    id: 'two-sum',
    title: 'Two Sum · hash map',
    language: 'python',
    code: `def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []


print(two_sum([2, 7, 11, 15, 4], 15))
`,
  },
  {
    id: 'lcs',
    title: 'LCS · DP matrix',
    language: 'python',
    code: `def lcs(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[len(a)][len(b)]


print(lcs("ABCB", "BCB"))
`,
  },
  {
    id: 'fib-memo',
    title: 'Fibonacci · recursion',
    language: 'python',
    code: `def fib(n, memo=None):
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n < 2:
        return n
    memo[n] = fib(n - 1, memo) + fib(n - 2, memo)
    return memo[n]


print(fib(6))
`,
  },
  {
    id: 'js-quick',
    title: 'Quick Sort · JavaScript',
    language: 'javascript',
    code: `function quickSort(arr, lo = 0, hi = arr.length - 1) {
  if (lo < hi) {
    const p = partition(arr, lo, hi);
    quickSort(arr, lo, p - 1);
    quickSort(arr, p + 1, hi);
  }
  return arr;
}

function partition(arr, lo, hi) {
  const pivot = arr[hi];
  let i = lo - 1;
  for (let j = lo; j < hi; j++) {
    if (arr[j] <= pivot) {
      i++;
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  }
  [arr[i + 1], arr[hi]] = [arr[hi], arr[i + 1]];
  return i + 1;
}

console.log(quickSort([9, 4, 7, 1, 3]));
`,
  },
  {
    id: 'cpp-dfs',
    title: 'DFS · C++',
    language: 'cpp',
    code: `#include <iostream>
#include <vector>
using namespace std;

void dfs(int node, vector<vector<int>>& adj, vector<bool>& visited) {
    visited[node] = true;
    cout << node << " ";
    for (int next : adj[node]) {
        if (!visited[next]) {
            dfs(next, adj, visited);
        }
    }
}

int main() {
    vector<vector<int>> adj = {{1, 2}, {3}, {3}, {}};
    vector<bool> visited(4, false);
    dfs(0, adj, visited);
    return 0;
}
`,
  },
];
