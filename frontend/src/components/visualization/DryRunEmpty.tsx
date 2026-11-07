/**
 * What the Dry Run tab shows when there are no steps (yet): live progress while
 * the AI model traces non-Python code, or the reason + a retry button.
 */
import { motion } from 'framer-motion';
import { Cpu, RefreshCw, Sparkles } from 'lucide-react';

import { useAnalysis } from '../../hooks/useAnalysis';
import { useAppStore } from '../../stores/appStore';
import type { DryRun } from '../../types';
import { LoadingOrb } from '../ui/LoadingOrb';
import { GlowButton } from '../ui/GlowButton';

export function DryRunEmpty({ dryRun }: { dryRun: DryRun }) {
  const status = useAppStore((s) => s.status);
  const stage = useAppStore((s) => s.stage);
  const chars = useAppStore((s) => s.llmChars);
  const language = useAppStore((s) => s.result?.language);
  const warnings = useAppStore((s) => s.result?.warnings ?? []);
  const { analyze } = useAnalysis();

  if (status === 'analyzing') {
    const tracing = /tracing/i.test(stage);
    return (
      <div className="flex flex-col items-center">
        <LoadingOrb message={tracing ? stage : stage || 'Analysing…'} chars={tracing ? chars : 0} />
        {dryRun.input_example && (
          <p className="-mt-4 font-mono text-xs" style={{ color: 'var(--text-faint)' }}>input: {dryRun.input_example}</p>
        )}
        <motion.p className="mt-3 max-w-md text-center text-xs" style={{ color: 'var(--text-faint)' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {language === 'python'
            ? 'Running your code in the sandbox…'
            : 'Only Python can be traced live, so the AI model is working through the steps by hand. Explain and Complexity fill in first; this can take a little while on a laptop.'}
        </motion.p>
      </div>
    );
  }

  const aiFailed = warnings.some((w) => /usable dry run|dry run failed/.test(w));
  const noModel = warnings.some((w) => /No AI model reachable|AI model unavailable/.test(w));
  const message =
    dryRun.error ??
    (aiFailed
      ? "The AI model's trace couldn't be read this time. Small models sometimes go off-format — retrying usually works."
      : noModel
        ? 'Only Python is traced live. For other languages start Ollama (./start.sh does this) so the AI model can generate the trace.'
        : 'No execution steps were produced for this code.');
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
      {aiFailed ? <Sparkles size={28} aria-hidden /> : <Cpu size={28} aria-hidden />}
      <p className="max-w-md">{message}</p>
      {(aiFailed || noModel) && (
        <GlowButton icon={<RefreshCw size={15} />} onClick={() => void analyze()}>
          Retry
        </GlowButton>
      )}
    </div>
  );
}
