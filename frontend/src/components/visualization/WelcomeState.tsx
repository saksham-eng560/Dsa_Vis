/** Empty results pane: a calm prompt plus one-click examples. */
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

import { useAnalysis } from '../../hooks/useAnalysis';
import { useAppStore } from '../../stores/appStore';
import { PRESETS } from '../../utils/presets';

const EASE = [0.22, 1, 0.36, 1] as const;

export function WelcomeState() {
  const { analyze } = useAnalysis();
  const quick = PRESETS.filter((p) => ['bubble', 'bfs', 'bst', 'reverse-list', 'lcs', 'two-sum'].includes(p.id));
  return (
    <div className="flex h-full flex-col justify-center px-2 py-10 md:px-8">
      <motion.p className="eyebrow" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}>Workspace</motion.p>
      <motion.h2 className="display mt-2 text-4xl md:text-5xl" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: EASE }}>
        Write code. <span style={{ color: 'var(--text-faint)' }}>Watch it run.</span>
      </motion.h2>
      <motion.p className="mt-4 max-w-lg text-[17px] leading-relaxed" style={{ color: 'var(--text-muted)' }} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: EASE, delay: 0.1 }}>
        Paste anything in the editor and press <b>Analyze</b>, or start from one of these.
      </motion.p>
      <motion.div className="mt-8 grid gap-2 sm:grid-cols-2" initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.06, delayChildren: 0.2 } } }}>
        {quick.map((p) => (
          <motion.button
            key={p.id}
            variants={{ hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } } }}
            whileHover={{ scale: 1.015 }}
            whileTap={{ scale: 0.985 }}
            className="focus-ring group flex items-center justify-between rounded-2xl px-5 py-4 text-left"
            style={{ background: 'var(--surface-2)' }}
            onClick={() => {
              const { setCode, setLanguage, setEntryCall } = useAppStore.getState();
              setCode(p.code);
              setLanguage(p.language);
              setEntryCall(p.entryCall ?? '');
              void analyze();
            }}
          >
            <span>
              <span className="block text-[15px] font-semibold">{p.title.split(' · ')[0]}</span>
              <span className="text-[13px]" style={{ color: 'var(--text-faint)' }}>{p.title.split(' · ')[1] ?? p.language}</span>
            </span>
            <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" style={{ color: 'var(--accent-primary)' }} aria-hidden />
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}
