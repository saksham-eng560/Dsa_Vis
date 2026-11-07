/** Accumulated stdout up to the current step (+ runtime error, if any). */
import { Terminal } from 'lucide-react';

export function OutputPanel({ output, error }: { output: string; error: string | null }) {
  return (
    <div className="glass-inset flex min-h-0 flex-col p-3">
      <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
        <Terminal size={13} aria-hidden /> Output
      </h3>
      <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs scroll-thin" aria-live="polite">
        {output || <span style={{ color: 'var(--text-faint)' }}>(no output yet)</span>}
        {error && <span style={{ color: 'var(--accent-danger)' }}>{`\n${error}`}</span>}
      </pre>
    </div>
  );
}
