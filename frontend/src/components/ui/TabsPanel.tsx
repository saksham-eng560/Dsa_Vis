/** Accessible tab strip (roving arrow-key focus) with an animated indicator. */
import { motion } from 'framer-motion';
import { useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface TabDef<T extends string> {
  id: T;
  label: string;
  icon?: ReactNode;
  badge?: string | number;
}

interface TabsPanelProps<T extends string> {
  tabs: TabDef<T>[];
  active: T;
  onChange: (id: T) => void;
  idPrefix: string;
}

export function TabsPanel<T extends string>({ tabs, active, onChange, idPrefix }: TabsPanelProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: KeyboardEvent, index: number) => {
    const delta = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!delta) return;
    e.preventDefault();
    const next = (index + delta + tabs.length) % tabs.length;
    const tab = tabs[next];
    if (tab) onChange(tab.id);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label="Analysis views" className="glass-inset flex gap-1 overflow-x-auto p-1 scroll-thin">
      {tabs.map((tab, i) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            id={`${idPrefix}-tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(e) => onKey(e, i)}
            className="focus-ring relative flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-[0.65rem] px-3 py-2 text-sm font-medium transition-colors"
            style={{ color: selected ? 'var(--text)' : 'var(--text-muted)' }}
          >
            {selected && (
              <motion.span
                layoutId={`${idPrefix}-indicator`}
                className="absolute inset-0 rounded-[0.65rem]"
                style={{ background: 'var(--glass-bg-active)', border: '1px solid var(--glass-border-hover)' }}
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            <span className="relative flex items-center gap-2">
              {tab.icon}
              {tab.label}
              {tab.badge !== undefined && <span className="chip !py-0 !text-[0.65rem]">{tab.badge}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}
