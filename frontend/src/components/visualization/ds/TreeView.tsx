/** Tree layout via d3-hierarchy (`tree()`), keeping null slots so binary trees keep left/right shape. */
import { hierarchy, tree as d3tree } from 'd3-hierarchy';
import { useMemo } from 'react';

import type { Highlight, Scalar, TreeNode } from '../../../types';
import { NodeLinkSvg, type PositionedEdge, type PositionedNode } from './NodeLinkSvg';
import { EmptyState, show } from './shared';

interface Slot {
  node: TreeNode | null;
  key: string;
}

/** Heap arrays render as complete binary trees. */
export function heapToTree(values: Scalar[]): TreeNode | null {
  const build = (i: number): TreeNode | null =>
    i < values.length ? { id: String(i), value: values[i] ?? null, children: [build(2 * i + 1), build(2 * i + 2)] } : null;
  return build(0);
}

export function TreeView({ root, highlights }: { root: TreeNode | null; highlights: Highlight[] }) {
  const layout = useMemo(() => {
    if (!root) return null;
    const h = hierarchy<Slot>({ node: root, key: root.id }, (slot) => {
      const kids = slot.node?.children ?? [];
      if (!slot.node || kids.every((k) => k === null)) return null;
      return kids.map((k, i) => ({ node: k, key: k?.id ?? `${slot.key}-null-${i}` }));
    });
    const nodeSize: [number, number] = [56, 72];
    d3tree<Slot>().nodeSize(nodeSize)(h);
    const all = h.descendants();
    const xs = all.map((d) => d.x ?? 0);
    const minX = Math.min(...xs);
    const nodes: PositionedNode[] = [];
    const edges: PositionedEdge[] = [];
    all.forEach((d) => {
      if (!d.data.node) return;
      nodes.push({ id: d.data.node.id, label: show(d.data.node.value), x: (d.x ?? 0) - minX + 36, y: (d.y ?? 0) + 32 });
      if (d.parent?.data.node) edges.push({ id: `${d.parent.data.key}->${d.data.key}`, source: d.parent.data.node.id, target: d.data.node.id });
    });
    const width = Math.max(...xs) - minX + 72;
    const height = Math.max(...all.map((d) => d.y ?? 0)) + 72;
    return { nodes, edges, width: Math.max(width, 200), height };
  }, [root]);

  if (!layout) return <EmptyState text="Tree is empty (root is None)." />;
  return <NodeLinkSvg {...layout} highlights={highlights} directed ariaLabel="Tree" />;
}
