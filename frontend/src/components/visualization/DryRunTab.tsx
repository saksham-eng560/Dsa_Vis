/** Dry Run tab: step narration, animated data structure, controls, watch + output. */
import { motion } from 'framer-motion';
import type { ReactElement } from 'react';
import { AlertTriangle, CornerDownRight, CornerUpLeft, Cpu, Sparkles } from 'lucide-react';

import { useDryRunKeys, useDryRunPlayback } from '../../hooks/useDryRun';
import { useAppStore } from '../../stores/appStore';
import type { DryRun, DryRunStep } from '../../types';
import { DataStructureView } from './DataStructureView';
import { DryRunEmpty } from './DryRunEmpty';
import { DryRunPlayer } from './DryRunPlayer';
import { OutputPanel } from './OutputPanel';
import { VariableWatch } from './VariableWatch';

const EVENT_ICON: Record<DryRunStep['event'], ReactElement> = {
  line: <CornerDownRight size={15} aria-hidden />,
  call: <CornerDownRight size={15} aria-hidden style={{ color: 'var(--accent-secondary)' }} />,
  return: <CornerUpLeft size={15} aria-hidden style={{ color: 'var(--accent-purple)' }} />,
  exception: <AlertTriangle size={15} aria-hidden style={{ color: 'var(--accent-danger)' }} />,
};

export function DryRunTab({ dryRun, active }: { dryRun: DryRun; active: boolean }) {
  useDryRunPlayback();
  useDryRunKeys(active);
  const index = useAppStore((s) => s.step);
  const step = dryRun.steps[index];

  if (!dryRun.steps.length) return <DryRunEmpty dryRun={dryRun} />;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
        {dryRun.source === 'trace' ? (
          <span className="chip"><Cpu size={12} aria-hidden /> Traced from real execution</span>
        ) : (
          <span className="chip" style={{ color: 'var(--accent-warning)' }}><Sparkles size={12} aria-hidden /> AI-generated trace</span>
        )}
        {dryRun.input_example && <code className="chip font-mono">{dryRun.input_example}</code>}
        {dryRun.truncated && <span className="chip">truncated</span>}
      </div>

      {step && (
        <motion.div
          key={step.step}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-inset flex items-start gap-2 px-3 py-2.5 font-mono text-sm"
          style={{ paddingLeft: `${0.75 + Math.min(step.depth, 6) * 0.75}rem` }}
          aria-live="polite"
        >
          <span className="mt-0.5 shrink-0">{EVENT_ICON[step.event]}</span>
          <span className="min-w-0 break-words">{step.description}</span>
          {step.depth > 0 && <span className="chip ml-auto shrink-0">depth {step.depth}</span>}
        </motion.div>
      )}

      <div className="glass-inset min-h-[200px] p-3">
        <DataStructureView ds={step?.data_structure_state} />
      </div>

      <DryRunPlayer total={dryRun.steps.length} />

      <div className="grid gap-3 md:grid-cols-2">
        <VariableWatch step={step} />
        <OutputPanel output={step?.output_so_far ?? ''} error={index === dryRun.steps.length - 1 ? dryRun.error : null} />
      </div>
    </div>
  );
}
