/** Dry Run tab: step narration, animated data structure, controls, watch + output. */
import { motion } from 'framer-motion';
import type { ReactElement } from 'react';
import { AlertTriangle, CornerDownRight, CornerUpLeft, Cpu, Lightbulb, Sparkles } from 'lucide-react';

import { useDryRunKeys, useDryRunPlayback } from '../../hooks/useDryRun';
import { useAppStore } from '../../stores/appStore';
import type { DryRun, DryRunStep } from '../../types';
import { DataStructureView } from './DataStructureView';
import { RecursionTreeView } from './RecursionTreeView';
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
  const showTree = Boolean(dryRun.call_tree?.recursive && dryRun.plan?.show_recursion_tree !== false);
  const structures = step?.data_structures?.length ? step.data_structures : step?.data_structure_state ? [step.data_structure_state] : [];

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

      {dryRun.plan?.insight && (
        <p className="flex gap-2 rounded-2xl px-4 py-3 text-sm leading-relaxed" style={{ background: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)' }}>
          <Lightbulb size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--accent-primary)' }} aria-hidden />
          <span>{dryRun.plan.insight}</span>
        </p>
      )}

      {showTree && dryRun.call_tree && <RecursionTreeView tree={dryRun.call_tree} step={index} />}

      {structures.length > 0 ? (
        <div className={`grid gap-3 ${structures.length > 1 ? 'xl:grid-cols-2' : ''}`}>
          {structures.map((ds) => (
            <div key={ds.name} className="glass-inset min-h-[160px] p-3">
              <DataStructureView ds={ds} />
              {ds.caption && <p className="mt-2 text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>{ds.caption}</p>}
            </div>
          ))}
        </div>
      ) : (
        !showTree && (
          <div className="glass-inset min-h-[160px] p-3">
            <DataStructureView ds={null} />
          </div>
        )
      )}

      <DryRunPlayer total={dryRun.steps.length} />

      <div className="grid gap-3 md:grid-cols-2">
        <VariableWatch step={step} />
        <OutputPanel output={step?.output_so_far ?? ''} error={index === dryRun.steps.length - 1 ? dryRun.error : null} />
      </div>
    </div>
  );
}
