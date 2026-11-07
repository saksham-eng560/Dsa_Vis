/**
 * Graph via a deterministic d3-force simulation (run to rest synchronously).
 * Positions are cached per node-set so the layout stays stable across steps
 * and only colours animate while the algorithm runs.
 */
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type SimulationNodeDatum } from 'd3-force';
import { useMemo } from 'react';

import type { GraphState, Highlight } from '../../../types';
import { NodeLinkSvg } from './NodeLinkSvg';
import { EmptyState, show } from './shared';

const W = 520;
const H = 340;
const cache = new Map<string, Map<string, { x: number; y: number }>>();

interface SimNode extends SimulationNodeDatum {
  id: string;
}

function layoutGraph(graph: GraphState): Map<string, { x: number; y: number }> {
  const key = graph.nodes.map((n) => n.id).join('|') + '#' + graph.edges.map((e) => `${e.source}>${e.target}`).join('|');
  const hit = cache.get(key);
  if (hit) return hit;
  // seed on a circle for determinism (d3-force is otherwise random-free but order-dependent)
  const nodes: SimNode[] = graph.nodes.map((n, i) => {
    const a = (2 * Math.PI * i) / Math.max(graph.nodes.length, 1);
    return { id: n.id, x: W / 2 + 120 * Math.cos(a), y: H / 2 + 120 * Math.sin(a) };
  });
  const links = graph.edges.map((e) => ({ source: e.source, target: e.target }));
  const sim = forceSimulation(nodes)
    .force('link', forceLink<SimNode, { source: string; target: string }>(links).id((d) => d.id).distance(80))
    .force('charge', forceManyBody().strength(-360))
    .force('center', forceCenter(W / 2, H / 2))
    .force('collide', forceCollide(32))
    .stop();
  for (let i = 0; i < 300; i += 1) sim.tick();
  const out = new Map(nodes.map((n) => [n.id, { x: clamp(n.x ?? 0, 28, W - 28), y: clamp(n.y ?? 0, 28, H - 36) }]));
  cache.set(key, out);
  return out;
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

export function GraphView({ graph, highlights }: { graph: GraphState; highlights: Highlight[] }) {
  const positions = useMemo(() => layoutGraph(graph), [graph]);
  if (!graph.nodes.length) return <EmptyState text="Graph has no vertices yet." />;
  const nodes = graph.nodes.map((n) => ({ id: n.id, label: n.label, ...(positions.get(n.id) ?? { x: W / 2, y: H / 2 }) }));
  const edges = graph.edges.map((e, i) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    label: e.weight === null || e.weight === undefined ? undefined : show(e.weight),
  }));
  return <NodeLinkSvg nodes={nodes} edges={edges} highlights={highlights} width={W} height={H} directed={graph.directed} ariaLabel="Graph" />;
}
