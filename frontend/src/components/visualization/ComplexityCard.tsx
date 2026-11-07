/** Complexity tab: large Big-O badge, best/average/worst switch, reasoning, scaling chart, space. */
import { motion } from 'framer-motion';
import { Cpu, HardDrive, Sparkles } from 'lucide-react';
import { useState } from 'react';

import type { Complexity } from '../../types';
import { growth, normalize, TONE_CLASSES } from '../../utils/complexity';
import { ScalingChart } from './ScalingChart';

type Case = 'best' | 'average' | 'worst';
const CASES: Case[] = ['best', 'average', 'worst'];

export function ComplexityBadge({ notation, large = false }: { notation: string; large?: boolean }) {
  const tone = TONE_CLASSES[growth(notation).tone];
  return (
    <span className={`${tone} tone-badge inline-flex items-center rounded-xl font-mono font-bold ${large ? 'px-5 py-2 text-4xl md:text-5xl' : 'px-2 py-0.5 text-xs'}`}>
      {normalize(notation)}
    </span>
  );
}

export function ComplexityCard({ complexity }: { complexity: Complexity }) {
  const [which, setWhich] = useState<Case>('worst');
  const notation = complexity.time[which];
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
      <div className="flex flex-col gap-4">
        <div className="glass-inset flex flex-col items-center gap-4 p-6">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
            <Cpu size={14} aria-hidden /> Time complexity
            <span className="chip normal-case tracking-normal">
              {complexity.source === 'llm' ? <><Sparkles size={11} aria-hidden /> AI analysis</> : 'static estimate'}
            </span>
          </div>
          <motion.div key={notation} initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 18 }}>
            <ComplexityBadge notation={notation} large />
          </motion.div>
          <div role="radiogroup" aria-label="Case" className="flex gap-1 rounded-xl p-1" style={{ background: 'var(--glass-bg)' }}>
            {CASES.map((c) => (
              <button
                key={c}
                role="radio"
                aria-checked={which === c}
                onClick={() => setWhich(c)}
                className="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                style={which === c ? { background: 'var(--glass-bg-active)', color: 'var(--text)' } : { color: 'var(--text-muted)' }}
              >
                <span className="capitalize">{c}</span> <span className="font-mono opacity-70">{normalize(complexity.time[c])}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="glass-inset p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>Why</h3>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{complexity.time.explanation || 'No explanation available.'}</p>
        </div>
      </div>
      <div className="flex flex-col gap-4">
        <div className="glass-inset p-4">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>How it scales</h3>
          <ScalingChart notation={notation} />
        </div>
        <div className="glass-inset flex items-start gap-4 p-4">
          <HardDrive size={20} aria-hidden className="mt-1 shrink-0" style={{ color: 'var(--accent-primary)' }} />
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
              Space complexity <ComplexityBadge notation={complexity.space.complexity} />
            </div>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{complexity.space.explanation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
