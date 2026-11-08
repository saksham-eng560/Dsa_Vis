/** Slide-over history of past analyses (persisted in localStorage). */
import { AnimatePresence, motion } from 'framer-motion';
import { Clock, Trash2, X } from 'lucide-react';
import { useEffect } from 'react';

import { useAnalysis } from '../../hooks/useAnalysis';
import { useAppStore } from '../../stores/appStore';
import type { HistoryItem } from '../../types';
import { ComplexityBadge } from '../visualization/ComplexityCard';
import { GlowButton } from '../ui/GlowButton';

const ago = (t: number) => {
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(t).toLocaleDateString();
};

export function Sidebar() {
  const open = useAppStore((s) => s.sidebarOpen);
  const history = useAppStore((s) => s.history);
  const { setSidebar, clearHistory } = useAppStore.getState();
  const { analyze } = useAnalysis();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setSidebar(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, setSidebar]);

  const restore = (item: HistoryItem) => {
    const { setCode, setLanguage, setEntryCall } = useAppStore.getState();
    setCode(item.code);
    setLanguage(item.language);
    setEntryCall(item.entryCall);
    setSidebar(false);
    void analyze();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 z-30 bg-black/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSidebar(false)} />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-label="Analysis history"
            className="glass-strong fixed inset-y-3 left-3 z-40 flex w-[min(22rem,calc(100vw-1.5rem))] flex-col rounded-2xl p-4 shadow-2xl"
            initial={{ x: '-110%' }}
            animate={{ x: 0 }}
            exit={{ x: '-110%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 32 }}
          >
            <div className="mb-3 flex items-center gap-2">
              <Clock size={16} aria-hidden />
              <h2 className="font-semibold">History</h2>
              <span className="ml-auto" />
              {history.length > 0 && <GlowButton iconOnly aria-label="Clear history" icon={<Trash2 size={15} />} onClick={clearHistory} />}
              <GlowButton iconOnly aria-label="Close history" icon={<X size={16} />} onClick={() => setSidebar(false)} autoFocus />
            </div>
            {history.length === 0 ? (
              <p className="mt-8 text-center text-sm" style={{ color: 'var(--text-faint)' }}>Your analyses will appear here.</p>
            ) : (
              <ul className="flex-1 space-y-2 overflow-y-auto pr-1 scroll-thin">
                {history.map((h, i) => (
                  <motion.li key={h.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }}>
                    <button onClick={() => restore(h)} className="glass-inset glass-hover focus-ring w-full p-3 text-left">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">{h.title}</span>
                        <span className="ml-auto shrink-0"><ComplexityBadge notation={h.worst} /></span>
                      </div>
                      <pre className="mt-1 truncate font-mono text-[0.7rem]" style={{ color: 'var(--text-faint)' }}>{h.code.split('\n').find((l) => l.trim())}</pre>
                      <span className="text-[0.68rem]" style={{ color: 'var(--text-faint)' }}>{ago(h.createdAt)}</span>
                    </button>
                  </motion.li>
                ))}
              </ul>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
