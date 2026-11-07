/** Linked list as a row of nodes with arrows; a cycle draws a back-edge arc. */
import type { Highlight, Scalar } from '../../../types';
import { NodeLinkSvg } from './NodeLinkSvg';
import { EmptyState, show } from './shared';

interface LinkedListViewProps {
  nodes: { id: string; value: Scalar }[];
  cycleTo?: string | null;
  highlights: Highlight[];
}

const GAP = 84;

export function LinkedListView({ nodes, cycleTo, highlights }: LinkedListViewProps) {
  if (!nodes.length) return <EmptyState text="List is empty (head is None)." />;
  const placed = nodes.map((n, i) => ({ id: n.id, label: show(n.value), x: 40 + i * GAP, y: 96 }));
  const edges = nodes.slice(1).map((n, i) => ({ id: `${nodes[i]?.id}->${n.id}`, source: nodes[i]?.id ?? '', target: n.id }));
  const last = nodes[nodes.length - 1];
  if (cycleTo && last) edges.push({ id: `cycle-${cycleTo}`, source: last.id, target: cycleTo, curved: true } as (typeof edges)[number]);
  const width = Math.max(40 + nodes.length * GAP + 40, 240);
  return (
    <div className="overflow-x-auto scroll-thin">
      <div style={{ minWidth: Math.min(width, 1200) }}>
        <NodeLinkSvg nodes={placed} edges={edges} highlights={highlights} width={width} height={150} directed ariaLabel="Linked list" />
      </div>
      <p className="text-center font-mono text-xs" style={{ color: 'var(--text-faint)' }}>
        {cycleTo ? '↺ cycle detected' : '… → None'}
      </p>
    </div>
  );
}
