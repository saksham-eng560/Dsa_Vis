/**
 * Flowchart tab (lazy-loaded): ReactFlow canvas laid out with dagre, one view
 * per function. The node for the current dry-run line glows and the edge that
 * led to it animates. Supports zoom/pan/fit, PNG/SVG export and Mermaid copy.
 */
import {
  Background, BackgroundVariant, Controls, ReactFlow, ReactFlowProvider, useReactFlow, type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useEffect, useMemo, useRef, useState } from 'react';

import { useAppStore, useCurrentStep } from '../../stores/appStore';
import type { Flowchart } from '../../types';
import { flowGroups, groupForStep, groupLabel, layoutFlow, nodeForLine } from '../../utils/diagramHelpers';
import { EmptyState } from './ds/shared';
import { FlowExportMenu } from './FlowExportMenu';
import { FlowNodeCard, type FlowRFNode } from './FlowNodeCard';

const nodeTypes = { flow: FlowNodeCard };

function FlowCanvas({ chart }: { chart: Flowchart }) {
  const groups = useMemo(() => flowGroups(chart), [chart]);
  const step = useCurrentStep();
  const followStep = useAppStore((s) => s.playing || s.activeTab === 'dryrun' || s.step > 0);
  const stepGroup = groupForStep(step, groups);
  const [group, setGroup] = useState<string>(groups[0] ?? '');
  const prevActive = useRef<string | undefined>(undefined);
  const { fitView } = useReactFlow();

  useEffect(() => setGroup(groups[0] ?? ''), [groups]);
  useEffect(() => {
    if (followStep && stepGroup && stepGroup !== group) setGroup(stepGroup);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepGroup, followStep]);

  const { nodes: groupNodes, edges: groupEdges, positions } = useMemo(() => {
    const nodes = chart.nodes.filter((n) => n.group === group);
    const ids = new Set(nodes.map((n) => n.id));
    const edges = chart.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    return { nodes, edges, positions: layoutFlow(nodes, edges) };
  }, [chart, group]);

  const active = followStep && stepGroup === group ? nodeForLine(groupNodes, step?.line ?? null)?.id : undefined;
  const from = prevActive.current;
  useEffect(() => {
    prevActive.current = active;
  }, [active]);

  const rfNodes: FlowRFNode[] = groupNodes.map((n) => ({
    id: n.id,
    type: 'flow',
    position: positions.get(n.id) ?? { x: 0, y: 0 },
    data: { label: n.label, kind: n.type, line: n.line, active: n.id === active },
    draggable: true,
  }));
  const rfEdges: Edge[] = groupEdges.map((e, i) => {
    const hot = active !== undefined && e.target === active && e.source === from;
    return {
      id: `${e.source}-${e.target}-${i}`,
      source: e.source,
      target: e.target,
      label: e.label ?? undefined,
      type: 'smoothstep',
      animated: hot,
      style: { stroke: hot ? 'var(--accent-primary)' : 'var(--text-faint)', strokeWidth: hot ? 2.5 : 1.25 },
      labelStyle: { fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' },
      labelBgStyle: { fill: 'var(--surface-strong)' },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 4,
    };
  });

  useEffect(() => {
    const t = window.setTimeout(() => void fitView({ padding: 0.15, duration: 300 }), 30);
    return () => window.clearTimeout(t);
  }, [group, fitView]);

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {groups.map((g) => (
          <button
            key={g}
            onClick={() => setGroup(g)}
            className="chip focus-ring cursor-pointer font-mono transition-colors"
            style={g === group ? { background: 'var(--glass-bg-active)', color: 'var(--text)', borderColor: 'var(--accent-primary)' } : undefined}
            aria-pressed={g === group}
          >
            {groupLabel(g)}
          </button>
        ))}
        <span className="ml-auto" />
        <FlowExportMenu chart={chart} group={group} />
      </div>
      <div className="glass-inset relative min-h-[420px] flex-1 overflow-hidden" data-testid="flowchart-canvas">
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          nodesConnectable={false}
        >
          <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="var(--glass-border-hover)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function FlowchartView({ chart }: { chart: Flowchart }) {
  if (!chart.nodes.length) return <EmptyState text="No flowchart could be generated for this code." />;
  return (
    <ReactFlowProvider>
      <FlowCanvas chart={chart} />
    </ReactFlowProvider>
  );
}
