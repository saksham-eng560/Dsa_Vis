/** Reveals text progressively (respects reduced-motion). */
import { useEffect, useState, type ReactNode } from 'react';

interface TypewriterTextProps {
  text: string;
  /** Rich rendering shown once typing finishes (e.g. inline code, line links). */
  children?: ReactNode;
  /** Characters per second. */
  speed?: number;
  className?: string;
}

const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

export function TypewriterText({ text, speed = 90, className = '', children }: TypewriterTextProps) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setCount(text.length);
      return;
    }
    setCount(0);
    const step = Math.max(1, Math.round(speed / 30));
    const timer = window.setInterval(() => {
      setCount((c) => {
        if (c >= text.length) {
          window.clearInterval(timer);
          return c;
        }
        return Math.min(text.length, c + step);
      });
    }, 1000 / 30);
    return () => window.clearInterval(timer);
  }, [text, speed]);

  const done = count >= text.length;
  return (
    <p className={`${className} ${done ? '' : 'caret'}`} aria-label={text}>
      <span aria-hidden="true">{done && children ? children : text.slice(0, count).replace(/`/g, '')}</span>
    </p>
  );
}
