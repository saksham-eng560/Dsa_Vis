/** System-style activity indicator (12 fading ticks) with a status line. */
import { motion } from 'framer-motion';

interface LoadingOrbProps {
  message: string;
  /** Characters streamed from the model so far (0 hides the counter). */
  chars?: number;
}

export function LoadingOrb({ message, chars = 0 }: LoadingOrbProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 p-10" role="status" aria-live="polite">
      <div className="relative h-9 w-9" aria-hidden>
        {Array.from({ length: 12 }, (_, i) => (
          <motion.span
            key={i}
            className="absolute left-1/2 top-0 h-[28%] w-[8%] -translate-x-1/2 rounded-full"
            style={{ background: 'var(--text-muted)', transformOrigin: '50% 180%', rotate: `${i * 30}deg` }}
            animate={{ opacity: [1, 0.15] }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear', delay: (i / 12) - 1 }}
          />
        ))}
      </div>
      <div className="text-center">
        <p className="text-[15px] font-medium">{message || 'Analysing…'}</p>
        {chars > 0 && (
          <p className="mt-1 font-mono text-xs tabular-nums" style={{ color: 'var(--text-faint)' }}>
            {chars.toLocaleString()} characters from the model
          </p>
        )}
      </div>
    </div>
  );
}
