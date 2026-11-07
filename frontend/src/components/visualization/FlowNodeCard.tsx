/** Custom ReactFlow node: colour-coded by type, glows when it is the active step. */
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { memo } from 'react';

import { NODE_COLORS } from '../../styles/theme';
import type { NodeType } from '../../types';

export type FlowNodeData = { label: string; kind: NodeType; line: number | null; active: boolean };
export type FlowRFNode = Node<FlowNodeData, 'flow'>;

/** Hexagonal "diamond" that keeps long conditions readable. */
const DIAMOND = 'polygon(12px 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 12px 100%, 0 50%)';

const SHAPES: Record<NodeType, string> = {
  start: '9999px',
  end: '9999px',
  process: '0.75rem',
  io: '0.75rem',
  decision: '0.5rem',
};

function FlowNodeCardImpl({ data }: NodeProps<FlowRFNode>) {
  const color = NODE_COLORS[data.kind];
  return (
    <div className="relative" title={data.line ? `Line ${data.line}` : undefined}>
      <Handle type="target" position={Position.Top} className="!h-1.5 !w-1.5 !border-0" style={{ background: color }} />
      <div
        className="px-4 py-2.5 font-mono text-[12px] leading-[18px] transition-all duration-300"
        style={{
          borderRadius: SHAPES[data.kind],
          border: `${data.active ? 2.5 : 1.5}px solid ${color}`,
          background: `color-mix(in srgb, ${color} ${data.active ? 30 : 9}%, var(--surface-strong))`,
          boxShadow: data.active ? `0 0 0 4px color-mix(in srgb, ${color} 25%, transparent), 0 0 28px ${color}` : 'var(--glass-shadow)',
          color: 'var(--text)',
          whiteSpace: 'pre',
          textAlign: 'center',
          clipPath: data.kind === 'decision' ? DIAMOND : undefined,
          paddingInline: data.kind === 'decision' ? 24 : undefined,
          fontStyle: data.kind === 'io' ? 'italic' : undefined,
        }}
      >
        {data.label}
      </div>
      {data.line != null && (
        <span className="absolute -right-2 -top-2 rounded-full px-1.5 text-[9px] font-semibold" style={{ background: color, color: '#0f0b1a' }}>
          L{data.line}
        </span>
      )}
      <Handle type="source" position={Position.Bottom} className="!h-1.5 !w-1.5 !border-0" style={{ background: color }} />
    </div>
  );
}

export const FlowNodeCard = memo(FlowNodeCardImpl);
