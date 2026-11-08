/** Picks the renderer for the current step's data-structure snapshot. */
import { Boxes } from 'lucide-react';

import { HIGHLIGHT_COLORS } from '../../styles/theme';
import type { DataStructureState } from '../../types';
import { ArrayView } from './ds/ArrayView';
import { GraphView } from './ds/GraphView';
import { HashMapView } from './ds/HashMapView';
import { LinkedListView } from './ds/LinkedListView';
import { MatrixView } from './ds/MatrixView';
import { EmptyState } from './ds/shared';
import { StackView } from './ds/StackView';
import { heapToTree, TreeView } from './ds/TreeView';

const TITLES: Record<DataStructureState['type'], string> = {
  array: 'Array', matrix: 'Matrix', stack: 'Stack', queue: 'Queue', heap: 'Heap',
  hash_map: 'Hash map', linked_list: 'Linked list', tree: 'Tree', graph: 'Graph',
};

function Renderer({ ds }: { ds: DataStructureState }) {
  switch (ds.type) {
    case 'array':
      return <ArrayView values={ds.state.values ?? []} highlights={ds.highlights} />;
    case 'queue':
      return <ArrayView values={ds.state.values ?? []} highlights={ds.highlights} edgeLabels={['front', 'rear']} />;
    case 'stack':
      return <StackView values={ds.state.values ?? []} highlights={ds.highlights} />;
    case 'heap':
      return (
        <>
          <TreeView root={heapToTree(ds.state.values ?? [])} highlights={ds.highlights.map((h) => ({ ...h, target: String(h.target) }))} />
          <ArrayView values={ds.state.values ?? []} highlights={ds.highlights} />
        </>
      );
    case 'matrix':
      return <MatrixView rows={ds.state.rows ?? []} highlights={ds.highlights} />;
    case 'hash_map':
      return <HashMapView entries={ds.state.entries ?? []} highlights={ds.highlights} />;
    case 'linked_list':
      return <LinkedListView nodes={ds.state.nodes ?? []} edges={ds.state.edges} cycleTo={ds.state.cycle_to} highlights={ds.highlights} />;
    case 'tree':
      return <TreeView root={ds.state.root ?? null} highlights={ds.highlights} />;
    case 'graph':
      return <GraphView graph={{ nodes: ds.state.nodes ?? [], edges: ds.state.edges ?? [], directed: ds.state.directed ?? false }} highlights={ds.highlights} />;
  }
}

export function DataStructureView({ ds }: { ds: DataStructureState | null | undefined }) {
  if (!ds) return <EmptyState text="No data structure is in scope at this step." />;
  const legend = [...new Map(ds.highlights.filter((h) => h.label).map((h) => [h.label, h])).values()];
  return (
    <div>
      <div className="mb-1 flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
        <Boxes size={14} aria-hidden />
        <span className="font-semibold">{TITLES[ds.type]}</span>
        {ds.name && <code className="chip font-mono">{ds.name}</code>}
        <span className="ml-auto flex flex-wrap gap-1.5">
          {legend.slice(0, 6).map((h) => (
            <span key={h.label} className="chip font-mono" style={{ color: HIGHLIGHT_COLORS[h.color] }}>
              ● {h.label}
            </span>
          ))}
        </span>
      </div>
      <Renderer ds={ds} />
    </div>
  );
}
