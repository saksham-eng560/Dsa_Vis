/** Flowchart node: a clean card with a coloured type marker; the active step gets an accent ring. */
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { memo } from 'react';

import { NODE_COLORS } from '../../styles/theme';
import type { NodeType } from '../../types';

export type FlowNodeData = { label: string; kind: NodeType; line: number | null; active: boolean };
export type FlowRFNode = Node<FlowNodeData, 'flow'>;

const KIND_LABEL: Record<NodeType, string> = { start: 'Start', end: 'End', process: 'Step', decision: 'Decision', io: 'Return / I/O' };

function FlowNodeCardImpl({ data }: NodeProps<FlowRFNode>) {
  const color = NODE_COLORS[data.kind];
  const terminal = data.kind === 'start' || data.kind === 'end';
  return (
    <div
      className="relative transition-all duration-300"
      style={{
        borderRadius: terminal ? 999 : 14,
        background: data.active ? color : 'var(--surface-1)',
        border: `1px solid ${data.active ? color : 'var(--separator-strong)'}`,
        boxShadow: data.active ? `0 0 0 5px color-mix(in srgb, ${color} 28%, transparent), 0 12px 30px rgba(0,0,0,0.35)` : '0 4px 14px rgba(0,0,0,0.18)',
        transform: data.active ? 'scale(1.04)' : undefined,
        padding: terminal ? '8px 18px' : '8px 14px 10px',
        minWidth: 90,
      }}
      title={data.line ? `Line ${data.line}` : undefined}
    >
      <Handle type="target" position={Position.Top} className="!h-1.5 !w-1.5 !border-0" style={{ background: 'var(--separator-strong)' }} />
      {!terminal && (
        <div className="mb-1 flex items-center gap-1.5 text-[9.5px] font-semibold uppercase tracking-wider" style={{ color: data.active ? 'rgba(255,255,255,0.85)' : 'var(--text-faint)' }}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: data.active ? '#fff' : color }} />
          {KIND_LABEL[data.kind]}
          {data.line != null && <span className="ml-auto font-mono normal-case tracking-normal">L{data.line}</span>}
        </div>
      )}
      <div
        className="text-center font-mono text-[12px] leading-[18px]"
        style={{ whiteSpace: 'pre', color: data.active ? '#fff' : 'var(--text)', fontWeight: terminal ? 600 : 400 }}
      >
        {data.kind === 'decision' ? `${data.label}` : data.label}
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-1.5 !w-1.5 !border-0" style={{ background: 'var(--separator-strong)' }} />
    </div>
  );
}

export const FlowNodeCard = memo(FlowNodeCardImpl);
