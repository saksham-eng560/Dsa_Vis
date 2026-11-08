/**
 * "Walkthrough on your input": the key moments of the real execution trace —
 * each step where variables changed, phrased as cause → effect. Clicking a
 * moment opens that step in the dry run.
 */
import { Footprints } from 'lucide-react';

import { useJumpToLine } from '../../hooks/useJumpToLine';
import type { DryRun } from '../../types';

const MAX_MOMENTS = 10;

interface Moment {
  index: number;
  line: number | null;
  code: string;
  effect: string;
}

function moments(run: DryRun): Moment[] {
  const out: Moment[] = [];
  run.steps.forEach((s, i) => {
    const prev = run.steps[i - 1];
    if (!prev || !s.changed.length) return;
    const effect = s.changed
      .filter((k) => !k.startsWith('self.'))
      .slice(0, 3)
      .map((k) => `${k} = ${(s.variables[k] ?? '').slice(0, 60)}`)
      .join(', ');
    if (effect) out.push({ index: i, line: prev.line, code: prev.description.replace(/^Line \d+:\s*/, ''), effect });
  });
  if (out.length <= MAX_MOMENTS) return out;
  const stride = out.length / MAX_MOMENTS; // keep the story evenly spread, always including the last moment
  return Array.from({ length: MAX_MOMENTS }, (_, k) => out[Math.min(out.length - 1, Math.round(k * stride))]!).filter(
    (m, k, arr) => arr.findIndex((x) => x.index === m.index) === k,
  );
}

export function Walkthrough({ run }: { run: DryRun }) {
  const { toStep } = useJumpToLine();
  if (run.source !== 'trace' || !run.steps.length) return null;
  const items = moments(run);
  const result = /→ (?:result|.+?) = (.+)$/m.exec(run.steps[run.steps.length - 1]?.output_so_far ?? '')?.[1];
  if (!items.length) return null;
  return (
    <section className="glass-inset p-4">
      <h3 className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
        <Footprints size={14} aria-hidden /> Walkthrough on your input
      </h3>
      {run.input_example && <p className="mb-3 font-mono text-xs" style={{ color: 'var(--text-muted)' }}>{run.input_example}</p>}
      <ol className="relative space-y-1 border-l pl-4" style={{ borderColor: 'var(--glass-border-hover)' }}>
        {items.map((m) => (
          <li key={m.index}>
            <button
              onClick={() => toStep(m.index)}
              className="focus-ring group w-full rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-[var(--glass-bg-hover)]"
            >
              <span className="mr-2 font-mono text-[0.7rem]" style={{ color: 'var(--accent-primary)' }}>L{m.line}</span>
              <code className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>{m.code.slice(0, 70)}</code>
              <span className="mx-1.5" style={{ color: 'var(--text-faint)' }}>→</span>
              <span className="font-mono text-xs" style={{ color: 'var(--accent-warning)' }}>{m.effect}</span>
            </button>
          </li>
        ))}
      </ol>
      {result && (
        <p className="mt-3 text-sm">
          Result: <code className="font-mono font-semibold" style={{ color: 'var(--accent-secondary)' }}>{result}</code>
        </p>
      )}
    </section>
  );
}
