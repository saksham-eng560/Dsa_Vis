/**
 * Linked list: nodes keep a fixed position (creation order) and arrows show the
 * *current* `next` pointers — so rewiring (e.g. reversal) is visible as arrows
 * flipping. Arrows that skip or point backwards are drawn as arcs.
 */
import type { Highlight, Scalar } from '../../../types';
import { NodeLinkSvg, type PositionedEdge } from './NodeLinkSvg';
import { EmptyState, show } from './shared';

interface LinkedListViewProps {
  nodes: { id: string; value: Scalar }[];
  edges?: { source: string; target: string }[];
  cycleTo?: string | null;
  highlights: Highlight[];
}

const GAP = 90;

export function LinkedListView({ nodes, edges, cycleTo, highlights }: LinkedListViewProps) {
  if (!nodes.length) return <EmptyState text="List is empty (head is None)." />;
  const index = new Map(nodes.map((n, i) => [n.id, i]));
  const placed = nodes.map((n, i) => ({ id: n.id, label: show(n.value), x: 44 + i * GAP, y: 110 }));
  const links = edges ?? nodes.slice(1).map((n, i) => ({ source: nodes[i]?.id ?? '', target: n.id }));
  const drawn: PositionedEdge[] = links.map((e) => ({
    id: `${e.source}->${e.target}`,
    source: e.source,
    target: e.target,
    curved: (index.get(e.target) ?? 0) !== (index.get(e.source) ?? 0) + 1,
  }));
  const last = nodes[nodes.length - 1];
  if (!edges && cycleTo && last) drawn.push({ id: `cycle-${cycleTo}`, source: last.id, target: cycleTo, curved: true });
  const width = Math.max(44 + nodes.length * GAP + 30, 240);
  const pointsNowhere = nodes.filter((n) => !links.some((e) => e.source === n.id)).map((n) => n.id);
  return (
    <div className="overflow-x-auto scroll-thin">
      <div style={{ minWidth: Math.min(width, 1200) }}>
        <NodeLinkSvg nodes={placed} edges={drawn} highlights={highlights} width={width} height={170} directed ariaLabel="Linked list" />
      </div>
      <p className="text-center font-mono text-xs" style={{ color: 'var(--text-faint)' }}>
        {edges
          ? `${pointsNowhere.length} node${pointsNowhere.length === 1 ? '' : 's'} point${pointsNowhere.length === 1 ? 's' : ''} to null · arrows show the current next pointers`
          : cycleTo
            ? '↺ cycle detected'
            : '… → null'}
      </p>
    </div>
  );
}
