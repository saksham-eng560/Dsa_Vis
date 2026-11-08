/**
 * Resizable two-pane layout. Drag the divider (mouse/touch/pen), use ←/→ when
 * it's focused, or double-click to reset. The split is remembered per browser.
 * Below `stackBelow` px the panes stack vertically.
 */
import { motion } from 'framer-motion';
import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';

import { loadJSON, saveJSON } from '../../utils/storage';

interface SplitPaneProps {
  left: ReactNode;
  right: ReactNode;
  storageKey: string;
  defaultRatio?: number;
  minLeftPx?: number;
  minRightPx?: number;
  stackBelow?: number;
  className?: string;
}

function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia?.(query).matches ?? false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const on = () => setMatches(mql.matches);
    mql.addEventListener('change', on);
    return () => mql.removeEventListener('change', on);
  }, [query]);
  return matches;
}

export function SplitPane({
  left, right, storageKey, defaultRatio = 0.42, minLeftPx = 320, minRightPx = 420, stackBelow = 1024, className = '',
}: SplitPaneProps) {
  const stacked = useMedia(`(max-width: ${stackBelow - 1}px)`);
  const container = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(() => loadJSON<number>(storageKey, defaultRatio));
  const [dragging, setDragging] = useState(false);

  const clamp = useCallback(
    (r: number) => {
      const w = container.current?.clientWidth ?? 1200;
      return Math.min(Math.max(r, minLeftPx / w), 1 - minRightPx / w);
    },
    [minLeftPx, minRightPx],
  );
  const commit = useCallback((r: number) => {
    setRatio(r);
    saveJSON(storageKey, r);
  }, [storageKey]);

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!dragging || !container.current) return;
    const rect = container.current.getBoundingClientRect();
    setRatio(clamp((e.clientX - rect.left) / rect.width));
  };
  const onPointerUp = () => {
    if (!dragging) return;
    setDragging(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    commit(ratio);
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const delta = e.key === 'ArrowLeft' ? -0.02 : e.key === 'ArrowRight' ? 0.02 : 0;
    if (!delta) return;
    e.preventDefault();
    commit(clamp(ratio + delta));
  };

  if (stacked) {
    return (
      <div className={`flex flex-col gap-4 ${className}`}>
        {left}
        {right}
      </div>
    );
  }

  return (
    <div ref={container} className={`flex min-h-0 ${className}`}>
      <div className="flex min-h-0 min-w-0 flex-col" style={{ width: `${clamp(ratio) * 100}%` }}>
        {left}
      </div>
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize editor and results"
        aria-valuenow={Math.round(ratio * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        tabIndex={0}
        data-dragging={dragging}
        className="split-handle focus-ring group flex w-4 shrink-0 items-center justify-center"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onDoubleClick={() => commit(clamp(defaultRatio))}
        onKeyDown={onKey}
        title="Drag to resize · double-click to reset"
      >
        <motion.span layout className="grip block h-10 w-1 rounded-full" style={{ background: 'var(--separator-strong)' }} />
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">{right}</div>
    </div>
  );
}
