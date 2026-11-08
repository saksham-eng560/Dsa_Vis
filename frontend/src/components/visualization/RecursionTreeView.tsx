/**
 * Recursion tree from the real trace. Calls appear as they happen; the
 * current call is solid blue, the call stack (active path) is tinted blue,
 * finished calls show their return value, and calls that recompute an
 * already-solved subproblem are orange. Click a call to jump to it.
 */
import { hierarchy, tree as d3tree, type HierarchyPointNode } from 'd3-hierarchy';
import { AnimatePresence, motion } from 'framer-motion';
import { GitFork, Maximize2, Minimize2 } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';

import { useFitScale } from '../../hooks/useFitScale';
import { useJumpToLine } from '../../hooks/useJumpToLine';
import type { CallNode, CallTree } from '../../types';

const NODE_H = 26;
const LEVEL_GAP = 58;
const MAX_H = 380;

interface TreeDatum {
  node: CallNode | null; // null = synthetic root for several top-level calls
  children: TreeDatum[];
}

function label(n: CallNode) {
  return `${n.func}(${n.args})`;
}
const widthOf = (n: CallNode) => Math.min(Math.max(label(n).length * 6.6 + 18, 48), 170);

export function RecursionTreeView({ tree, step }: { tree: CallTree; step: number }) {
  const { toStep } = useJumpToLine();
  const [fit, setFit] = useState(true);
  const box = useRef<HTMLDivElement>(null);

  const visible = useMemo(() => tree.nodes.filter((n) => n.start <= step), [tree.nodes, step]);
  const active = useMemo(() => new Set(visible.filter((n) => n.end === null || n.end >= step).map((n) => n.id)), [visible, step]);
  const current = useMemo(() => {
    let best: CallNode | undefined;
    for (const n of visible) if (active.has(n.id) && (!best || n.start > best.start)) best = n;
    return best;
  }, [visible, active]);

  const layout = useMemo(() => {
    if (!visible.length) return null;
    const byId = new Map<number, TreeDatum>(visible.map((n) => [n.id, { node: n, children: [] }]));
    const roots: TreeDatum[] = [];
    for (const n of visible) {
      const parent = n.parent !== null ? byId.get(n.parent) : undefined;
      (parent ? parent.children : roots).push(byId.get(n.id)!);
    }
    const rootDatum: TreeDatum = roots.length === 1 ? roots[0]! : { node: null, children: roots };
    const maxW = Math.max(...visible.map(widthOf));
    const h = hierarchy(rootDatum, (d) => d.children);
    d3tree<TreeDatum>().nodeSize([maxW + 14, LEVEL_GAP]).separation((a, b) => (a.parent === b.parent ? 1 : 1.15))(h);
    const pts = h.descendants().filter((d) => d.data.node) as HierarchyPointNode<TreeDatum>[];
    const xs = pts.map((d) => d.x);
    const ys = pts.map((d) => d.y);
    const minX = Math.min(...xs) - maxW / 2 - 12;
    const minY = Math.min(...ys) - NODE_H;
    return {
      pts,
      links: h.links().filter((l) => l.source.data.node && l.target.data.node) as { source: HierarchyPointNode<TreeDatum>; target: HierarchyPointNode<TreeDatum> }[],
      minX,
      minY,
      width: Math.max(...xs) - minX + maxW / 2 + 12,
      height: Math.max(...ys) - minY + NODE_H + 22,
    };
  }, [visible]);

  const scale = useFitScale(box, layout?.width ?? 0, layout?.height ?? 0, MAX_H);
  const zoom = fit ? scale : 1;

  const maxDepth = useMemo(() => {
    const depth = new Map<number, number>();
    let max = 0;
    for (const n of tree.nodes) {
      const d = n.parent !== null ? (depth.get(n.parent) ?? 0) + 1 : 0;
      depth.set(n.id, d);
      max = Math.max(max, d);
    }
    return max + 1;
  }, [tree.nodes]);

  return (
    <section className="glass-inset p-4">
      <header className="mb-3 flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
        <GitFork size={14} aria-hidden />
        <span className="text-[13px] font-semibold" style={{ color: 'var(--text)' }}>Recursion tree</span>
        <span className="chip">{visible.length} / {tree.nodes.length} calls</span>
        <span className="chip">max depth {maxDepth}</span>
        {tree.repeated > 0 && (
          <span className="chip" style={{ color: 'var(--accent-orange)' }}>{tree.repeated} recomputed</span>
        )}
        {tree.cache_hits > 0 && (
          <span className="chip" style={{ color: 'var(--accent-secondary)' }}>{tree.cache_hits} cache hits</span>
        )}
        <span className="ml-auto flex items-center gap-3">
          <Legend color="var(--accent-primary)" text="current" />
          <Legend color="color-mix(in srgb, var(--accent-primary) 35%, var(--surface-3))" text="on the stack" />
          <Legend color="var(--surface-3)" text="returned" />
          {tree.repeated > 0 && <Legend color="var(--accent-orange)" text="recomputed" ring />}
          {tree.cache_hits > 0 && <Legend color="var(--accent-secondary)" text="cache hit" ring />}
          <button className="chip focus-ring cursor-pointer" onClick={() => setFit(!fit)} aria-label={fit ? 'Show at full size' : 'Fit to panel'}>
            {fit ? <Maximize2 size={11} /> : <Minimize2 size={11} />} {fit ? `${Math.round(scale * 100)}% · 100%` : 'Fit'}
          </button>
        </span>
      </header>
      {!layout ? (
        <p className="py-8 text-center text-sm" style={{ color: 'var(--text-faint)' }}>The first call appears as soon as it is made.</p>
      ) : (
        <div ref={box} className="overflow-auto scroll-thin" style={{ maxHeight: fit ? MAX_H + 8 : 520 }}>
          <svg
            viewBox={`${layout.minX} ${layout.minY} ${layout.width} ${layout.height}`}
            width={layout.width * zoom}
            height={layout.height * zoom}
            className="mx-auto block"
            role="img"
            aria-label={`Recursion tree with ${visible.length} calls`}
          >
            {layout.links.map((l) => {
              const hot = active.has(l.target.data.node!.id);
              return (
                <motion.line
                  key={`${l.source.data.node!.id}-${l.target.data.node!.id}`}
                  x1={l.source.x} y1={l.source.y + NODE_H / 2} x2={l.target.x} y2={l.target.y - NODE_H / 2}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  stroke={hot ? 'var(--accent-primary)' : 'var(--separator-strong)'} strokeWidth={hot ? 2 : 1.25}
                />
              );
            })}
            <AnimatePresence>
              {layout.pts.map((p) => {
                const n = p.data.node!;
                const isCurrent = n.id === current?.id;
                const onStack = active.has(n.id);
                const returned = n.end !== null && n.end < step;
                const w = widthOf(n);
                const fill = isCurrent ? 'var(--accent-primary)' : onStack ? 'color-mix(in srgb, var(--accent-primary) 30%, var(--surface-2))' : 'var(--surface-3)';
                return (
                  <motion.g
                    key={n.id}
                    initial={{ opacity: 0, scale: 0.6, x: p.x, y: p.y - 12 }}
                    animate={{ opacity: 1, scale: 1, x: p.x, y: p.y }}
                    transition={{ type: 'spring', stiffness: 320, damping: 26 }}
                    style={{ cursor: 'pointer' }}
                    onClick={() => toStep(n.start)}
                  >
                    <title>{`${label(n)}${n.ret !== null ? ` → ${n.ret}` : ''} · step ${n.start + 1}${n.cached ? ' · answered from the cache' : n.repeat ? ` · computed ${n.repeat + 1}× so far` : ''}`}</title>
                    <rect
                      x={-w / 2} y={-NODE_H / 2} width={w} height={NODE_H} rx={NODE_H / 2}
                      fill={fill}
                      stroke={n.cached ? 'var(--accent-secondary)' : n.repeat ? 'var(--accent-orange)' : 'none'}
                      strokeWidth={n.repeat ? 2 : 0}
                      strokeDasharray={n.cached ? '4 3' : undefined}
                    />
                    <text textAnchor="middle" dy="0.35em" fontSize={11} fontFamily="var(--font-mono)" fill={isCurrent ? '#fff' : 'var(--text)'} fontWeight={isCurrent ? 600 : 400}>
                      {label(n).length > 26 ? `${label(n).slice(0, 25)}…` : label(n)}
                    </text>
                    {returned && n.ret !== null && (
                      <motion.text
                        initial={{ opacity: 0, y: NODE_H / 2 + 6 }} animate={{ opacity: 1, y: NODE_H / 2 + 14 }}
                        textAnchor="middle" fontSize={11} fontWeight={600} fontFamily="var(--font-mono)"
                        fill={n.repeat && !n.cached ? 'var(--accent-orange)' : 'var(--accent-secondary)'}
                      >
                        → {n.ret.length > 14 ? `${n.ret.slice(0, 13)}…` : n.ret}
                      </motion.text>
                    )}
                  </motion.g>
                );
              })}
            </AnimatePresence>
          </svg>
        </div>
      )}
      {tree.truncated && (
        <p className="mt-2 text-xs" style={{ color: 'var(--text-faint)' }}>Showing the first {tree.nodes.length} calls.</p>
      )}
    </section>
  );
}

function Legend({ color, text, ring = false }: { color: string; text: string; ring?: boolean }) {
  return (
    <span className="hidden items-center gap-1.5 xl:flex">
      <span className="h-2.5 w-4 rounded-full" style={ring ? { border: `2px solid ${color}` } : { background: color }} />
      {text}
    </span>
  );
}
