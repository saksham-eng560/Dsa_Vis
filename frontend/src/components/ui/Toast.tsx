/** Minimal toast notifications backed by a tiny Zustand store. */
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, Info, XCircle } from 'lucide-react';
import { create } from 'zustand';

type ToastKind = 'success' | 'error' | 'info';
interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastStore {
  toasts: ToastItem[];
  push: (kind: ToastKind, message: string) => void;
  dismiss: (id: number) => void;
}

export const useToasts = create<ToastStore>((set, get) => ({
  toasts: [],
  push: (kind, message) => {
    const id = Date.now() + Math.random();
    set({ toasts: [...get().toasts, { id, kind, message }].slice(-4) });
    window.setTimeout(() => get().dismiss(id), 4200);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

/** Imperative helper usable outside React components. */
export const toast = (kind: ToastKind, message: string) => useToasts.getState().push(kind, message);

const ICONS = {
  success: <CheckCircle2 size={16} style={{ color: 'var(--accent-secondary)' }} />,
  error: <XCircle size={16} style={{ color: 'var(--accent-danger)' }} />,
  info: <Info size={16} style={{ color: 'var(--accent-primary)' }} />,
};

export function ToastViewport() {
  const { toasts, dismiss } = useToasts();
  return (
    <div className="pointer-events-none fixed left-1/2 top-16 z-50 flex -translate-x-1/2 flex-col items-center gap-2" aria-live="polite">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.button
            key={t.id}
            layout
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            onClick={() => dismiss(t.id)}
            className="glass-strong pointer-events-auto flex max-w-sm items-center gap-2 rounded-full px-5 py-2.5 text-left text-sm shadow-2xl"
          >
            {ICONS[t.kind]}
            <span>{t.message}</span>
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}
