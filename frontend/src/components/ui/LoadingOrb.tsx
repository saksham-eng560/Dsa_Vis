/** Morphing glass orb shown while the pipeline / LLM is working. */
import { motion } from 'framer-motion';

interface LoadingOrbProps {
  message: string;
  /** Characters streamed from the LLM so far (0 hides the counter). */
  chars?: number;
}

export function LoadingOrb({ message, chars = 0 }: LoadingOrbProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8" role="status" aria-live="polite">
      <div className="relative h-28 w-28">
        <motion.div
          className="absolute inset-0"
          style={{
            background: 'conic-gradient(from 0deg, #818cf8, #34d399, #c084fc, #818cf8)',
            filter: 'blur(14px)',
            opacity: 0.75,
          }}
          animate={{
            rotate: 360,
            borderRadius: ['42% 58% 70% 30% / 45% 45% 55% 55%', '70% 30% 46% 54% / 30% 39% 61% 70%', '42% 58% 70% 30% / 45% 45% 55% 55%'],
          }}
          transition={{ rotate: { duration: 6, repeat: Infinity, ease: 'linear' }, borderRadius: { duration: 4, repeat: Infinity } }}
        />
        <motion.div
          className="glass absolute inset-3"
          animate={{ borderRadius: ['50%', '44% 56% 52% 48%', '50%'], scale: [1, 1.05, 1] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium">{message || 'Analysing…'}</p>
        {chars > 0 && (
          <p className="mt-1 font-mono text-xs" style={{ color: 'var(--text-faint)' }}>
            {chars.toLocaleString()} characters received from the model
          </p>
        )}
      </div>
    </div>
  );
}
