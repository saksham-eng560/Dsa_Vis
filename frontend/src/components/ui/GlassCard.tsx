/** Frosted-glass panel used for every major surface. */
import { motion, type HTMLMotionProps } from 'framer-motion';

interface GlassCardProps extends HTMLMotionProps<'section'> {
  /** Adds the subtle indigo glow used for focal panels. */
  glow?: boolean;
}

export function GlassCard({ glow = false, className = '', style, children, ...rest }: GlassCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className={`glass ${className}`}
      style={glow ? { boxShadow: 'var(--glass-shadow), var(--glass-shadow-glow)', ...style } : style}
      {...rest}
    >
      {children}
    </motion.section>
  );
}
