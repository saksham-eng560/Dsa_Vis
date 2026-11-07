/**
 * Generic animated node-link SVG used by tree, graph and linked-list views.
 * Layout is computed by the caller (d3-hierarchy / d3-force / linear); this
 * component only renders and springs nodes to their new positions.
 */
import { AnimatePresence, motion } from 'framer-motion';

import { HIGHLIGHT_COLORS } from '../../../styles/theme';
import type { Highlight } from '../../../types';
import { matching } from './shared';

export interface PositionedNode {
  id: string;
  label: string;
  x: number;
  y: number;
}

export interface PositionedEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  curved?: boolean;
}

interface NodeLinkSvgProps {
  nodes: PositionedNode[];
  edges: PositionedEdge[];
  highlights: Highlight[];
  width: number;
  height: number;
  directed?: boolean;
  radius?: number;
  ariaLabel: string;
}

const SPRING = { type: 'spring', stiffness: 170, damping: 22 } as const;

export function NodeLinkSvg({ nodes, edges, highlights, width, height, directed = false, radius = 20, ariaLabel }: NodeLinkSvgProps) {
  const pos = new Map(nodes.map((n) => [n.id, n]));
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mx-auto block h-auto w-full" style={{ maxHeight: 380, maxWidth: width * 1.4 }} role="img" aria-label={ariaLabel}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-faint)" />
        </marker>
      </defs>
      {edges.map((e) => {
        const a = pos.get(e.source);
        const b = pos.get(e.target);
        if (!a || !b) return null;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const [x1, y1] = [a.x + (dx / len) * radius, a.y + (dy / len) * radius];
        const [x2, y2] = [b.x - (dx / len) * (radius + 2), b.y - (dy / len) * (radius + 2)];
        const d = e.curved
          ? `M ${x1} ${y1} Q ${(a.x + b.x) / 2} ${Math.min(a.y, b.y) - 70} ${x2} ${y2}`
          : `M ${x1} ${y1} L ${x2} ${y2}`;
        return (
          <g key={e.id}>
            <motion.path
              animate={{ d }}
              transition={SPRING}
              fill="none"
              stroke="var(--glass-border-hover)"
              strokeWidth={2}
              markerEnd={directed ? 'url(#arrow)' : undefined}
            />
            {e.label && (
              <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 6} textAnchor="middle" fontSize={11} fill="var(--text-muted)" fontFamily="var(--font-mono)">
                {e.label}
              </text>
            )}
          </g>
        );
      })}
      <AnimatePresence>
        {nodes.map((n) => {
          const hs = matching(highlights, n.id);
          const main = hs.find((h) => h.color === 'red') ?? hs.find((h) => h.label !== 'visited') ?? hs[0];
          const color = main ? HIGHLIGHT_COLORS[main.color] : undefined;
          const pointers = hs.filter((h) => !['visited', 'frontier', 'changed'].includes(h.label)).map((h) => h.label);
          return (
            <motion.g
              key={n.id}
              initial={{ opacity: 0, scale: 0.4, x: n.x, y: n.y }}
              animate={{ opacity: 1, scale: 1, x: n.x, y: n.y }}
              exit={{ opacity: 0, scale: 0.4 }}
              transition={SPRING}
            >
              <motion.circle
                r={radius}
                animate={{
                  fill: color ? `color-mix(in srgb, ${color} 28%, transparent)` : 'var(--glass-bg-active)',
                  stroke: color ?? 'var(--glass-border-hover)',
                }}
                strokeWidth={2.5}
                style={{ filter: color ? `drop-shadow(0 0 8px ${color})` : undefined }}
              />
              <text textAnchor="middle" dy="0.35em" fontSize={13} fontWeight={600} fill="var(--text)" fontFamily="var(--font-mono)">
                {n.label.length > 5 ? `${n.label.slice(0, 4)}…` : n.label}
              </text>
              {pointers.length > 0 && (
                <text textAnchor="middle" y={radius + 15} fontSize={11} fontWeight={600} fill={color ?? 'var(--text-muted)'} fontFamily="var(--font-mono)">
                  {pointers.join(', ')}
                </text>
              )}
            </motion.g>
          );
        })}
      </AnimatePresence>
    </svg>
  );
}
