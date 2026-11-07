/** Button with glass styling, optional gradient glow and a click ripple. */
import { useState, type ButtonHTMLAttributes, type MouseEvent, type ReactNode } from 'react';

interface GlowButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'glass' | 'glow';
  icon?: ReactNode;
  /** Square icon-only button; `aria-label` is then required for accessibility. */
  iconOnly?: boolean;
}

interface Ripple {
  id: number;
  x: number;
  y: number;
  size: number;
}

export function GlowButton({
  variant = 'glass',
  icon,
  iconOnly = false,
  className = '',
  children,
  onClick,
  type = 'button',
  ...rest
}: GlowButtonProps) {
  const [ripples, setRipples] = useState<Ripple[]>([]);

  const handleClick = (e: MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const ripple = { id: Date.now(), x: e.clientX - rect.left - size / 2, y: e.clientY - rect.top - size / 2, size };
    setRipples((r) => [...r, ripple]);
    window.setTimeout(() => setRipples((r) => r.filter((x) => x.id !== ripple.id)), 650);
    onClick?.(e);
  };

  return (
    <button
      type={type}
      className={`btn ${variant === 'glow' ? 'btn-glow' : ''} ${iconOnly ? 'btn-icon' : ''} ${className}`}
      onClick={handleClick}
      {...rest}
    >
      {icon}
      {children}
      {ripples.map((r) => (
        <span key={r.id} className="ripple" style={{ left: r.x, top: r.y, width: r.size, height: r.size }} />
      ))}
    </button>
  );
}
