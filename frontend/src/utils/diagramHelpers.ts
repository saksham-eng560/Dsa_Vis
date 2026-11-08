/**
 * Flowchart helpers: dagre layered layout, group naming, step→node mapping and
 * Mermaid export (so diagrams can be pasted into Markdown/GitHub).
 */
import { Graph, layout } from '@dagrejs/dagre';

import type { DryRunStep, FlowEdge, FlowNode, Flowchart } from '../types';

export const PROGRAM_GROUP = '<program>';

/** Approximate node box size from its label (monospace, max 48 chars per line). */
export function nodeSize(node: FlowNode): { width: number; height: number } {
  const lines = node.label.split('\n');
  const longest = Math.max(...lines.map((l) => l.length), 4);
  const width = Math.min(Math.max(longest * 7.4 + 36, 110), 380);
  const terminal = node.type === 'start' || node.type === 'end';
  const height = lines.length * 18 + (terminal ? 22 : 42); // non-terminal cards carry a type label row
  return { width, height };
}

/** Top-to-bottom layered layout; returns top-left positions keyed by node id. */
export function layoutFlow(nodes: FlowNode[], edges: FlowEdge[]): Map<string, { x: number; y: number }> {
  const g = new Graph({ multigraph: true });
  g.setGraph({ rankdir: 'TB', nodesep: 36, ranksep: 54, marginx: 16, marginy: 16 });
  g.setDefaultEdgeLabel(() => ({}));
  const ids = new Set(nodes.map((n) => n.id));
  nodes.forEach((n) => g.setNode(n.id, nodeSize(n)));
  edges.forEach((e, i) => {
    if (ids.has(e.source) && ids.has(e.target)) g.setEdge(e.source, e.target, {}, `e${i}`);
  });
  layout(g);
  const out = new Map<string, { x: number; y: number }>();
  nodes.forEach((n) => {
    const p = g.node(n.id) as { x: number; y: number; width: number; height: number } | undefined;
    if (p) out.set(n.id, { x: p.x - p.width / 2, y: p.y - p.height / 2 });
  });
  return out;
}

/** Ordered list of groups (functions first, top-level program last). */
export function flowGroups(chart: Flowchart): string[] {
  const groups = [...new Set(chart.nodes.map((n) => n.group))];
  return groups.sort((a, b) => Number(a === PROGRAM_GROUP) - Number(b === PROGRAM_GROUP));
}

export const groupLabel = (group: string): string => (group === PROGRAM_GROUP ? 'Program' : `${group}()`);

/** Flowchart group corresponding to a dry-run step's function. */
export function groupForStep(step: DryRunStep | undefined, groups: string[]): string | undefined {
  if (!step) return undefined;
  if (step.function === '<module>') return groups.includes(PROGRAM_GROUP) ? PROGRAM_GROUP : undefined;
  return groups.find((g) => g === step.function || g.endsWith(`.${step.function}`));
}

/** Node whose source line range contains `line` (smallest range wins). */
export function nodeForLine(nodes: FlowNode[], line: number | null): FlowNode | undefined {
  if (line == null) return undefined;
  let best: FlowNode | undefined;
  for (const n of nodes) {
    if (n.line == null || n.type === 'end') continue;
    const end = n.end_line ?? n.line;
    if (line >= n.line && line <= end && (!best || end - n.line < (best.end_line ?? best.line ?? 0) - (best.line ?? 0))) {
      best = n;
    }
  }
  return best;
}

/** Serialise a flowchart group to Mermaid `flowchart TD` syntax. */
export function toMermaid(chart: Flowchart, group?: string): string {
  const nodes = chart.nodes.filter((n) => !group || n.group === group);
  const ids = new Set(nodes.map((n) => n.id));
  const esc = (s: string) => s.replace(/"/g, '#quot;').replace(/\n/g, '<br/>');
  const shape: Record<FlowNode['type'], [string, string]> = {
    start: ['([', '])'], end: ['([', '])'], decision: ['{', '}'], io: ['[/', '/]'], process: ['[', ']'],
  };
  const lines = ['flowchart TD'];
  nodes.forEach((n) => {
    const [open, close] = shape[n.type];
    lines.push(`  ${n.id}${open}"${esc(n.label)}"${close}`);
  });
  chart.edges
    .filter((e) => ids.has(e.source) && ids.has(e.target))
    .forEach((e) => lines.push(`  ${e.source} -->${e.label ? `|${esc(e.label)}|` : ''} ${e.target}`));
  return lines.join('\n');
}
