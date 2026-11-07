/** Theme tokens consumed from TypeScript (SVG fills, node colours). */
import type { HighlightColor, NodeType } from '../types';

/** CSS variable references so colours follow the active theme. */
export const HIGHLIGHT_COLORS: Record<HighlightColor, string> = {
  green: 'var(--accent-secondary)',
  red: 'var(--accent-danger)',
  yellow: 'var(--accent-warning)',
  blue: 'var(--accent-blue)',
  purple: 'var(--accent-purple)',
};

/** Flowchart node palette: start green, process blue, decision amber, I/O purple, end red. */
export const NODE_COLORS: Record<NodeType, string> = {
  start: 'var(--accent-secondary)',
  process: 'var(--accent-blue)',
  decision: 'var(--accent-warning)',
  io: 'var(--accent-purple)',
  end: 'var(--accent-danger)',
};

/** Shared spring for state transitions (snappy but soft). */
export const SPRING = { type: 'spring', stiffness: 260, damping: 26, mass: 0.8 } as const;
