/** Number that springs to its new value. */
import { animate } from 'framer-motion';
import { useEffect, useRef } from 'react';

export function AnimatedCounter({ value, className = '' }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(value);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const controls = animate(previous.current, value, {
      duration: 0.4,
      onUpdate: (v) => {
        node.textContent = Math.round(v).toString();
      },
    });
    previous.current = value;
    return () => controls.stop();
  }, [value]);

  return (
    <span ref={ref} className={`tabular-nums ${className}`}>
      {value}
    </span>
  );
}
