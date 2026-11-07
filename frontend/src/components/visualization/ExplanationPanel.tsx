/** Explain tab: typewriter summary, ELI5 toggle, concept tags, edge cases, optimisations, related patterns. */
import { AnimatePresence, motion } from 'framer-motion';
import { Baby, Lightbulb, Link as LinkIcon, ShieldAlert, Zap } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';

import { explain } from '../../services/api';
import { useAppStore } from '../../stores/appStore';
import type { AnalysisResult, Explanation } from '../../types';
import { TypewriterText } from '../shared/TypewriterText';
import { toast } from '../ui/Toast';

function Section({ icon, title, items }: { icon: ReactNode; title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="glass-inset p-4">
      <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
        {icon} {title}
      </h3>
      <motion.ul className="space-y-1.5 text-sm" initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.06 } } }}>
        {items.map((item) => (
          <motion.li key={item} variants={{ hidden: { opacity: 0, x: -6 }, show: { opacity: 1, x: 0 } }} className="flex gap-2" style={{ color: 'var(--text-muted)' }}>
            <span style={{ color: 'var(--accent-primary)' }}>•</span>
            {item}
          </motion.li>
        ))}
      </motion.ul>
    </div>
  );
}

export function ExplanationPanel({ result }: { result: AnalysisResult }) {
  const [eli5, setEli5] = useState(false);
  const [simple, setSimple] = useState<Explanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [openConcept, setOpenConcept] = useState<string | null>(null);
  const ctrl = useRef<AbortController | null>(null);

  useEffect(() => {
    setSimple(null);
    setEli5(false);
  }, [result]);

  const toggleEli5 = async () => {
    const next = !eli5;
    setEli5(next);
    if (!next || simple) return;
    ctrl.current?.abort();
    ctrl.current = new AbortController();
    setLoading(true);
    try {
      setSimple(await explain(useAppStore.getState().code, result.language, true, ctrl.current.signal));
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        toast('error', (err as Error).message);
        setEli5(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const view = eli5 && simple ? simple : result;
  return (
    <div className="flex flex-col gap-4">
      <div className="glass-inset p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold">{view.algorithm_name}</h3>
          <button
            role="switch"
            aria-checked={eli5}
            onClick={() => void toggleEli5()}
            className="focus-ring ml-auto flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium transition-colors"
            style={{ borderColor: eli5 ? 'var(--accent-secondary)' : 'var(--glass-border)', color: eli5 ? 'var(--accent-secondary)' : 'var(--text-muted)' }}
          >
            <Baby size={14} aria-hidden /> Explain like I'm 5
          </button>
        </div>
        {loading ? (
          <p className="animate-pulse text-sm" style={{ color: 'var(--text-faint)' }}>Simplifying…</p>
        ) : (
          <TypewriterText key={`${eli5}-${view.summary}`} text={view.summary} className="text-[0.95rem] leading-relaxed" />
        )}
        {eli5 && simple && !simple.llm_used && (
          <p className="mt-2 text-xs" style={{ color: 'var(--text-faint)' }}>Start the AI model for a simplified explanation.</p>
        )}
      </div>

      {view.key_concepts.length > 0 && (
        <div className="glass-inset p-4">
          <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
            <Lightbulb size={14} aria-hidden /> Key concepts
          </h3>
          <div className="flex flex-wrap gap-2">
            {view.key_concepts.map((c) => (
              <button
                key={c.concept}
                onClick={() => setOpenConcept(openConcept === c.concept ? null : c.concept)}
                aria-expanded={openConcept === c.concept}
                className="chip focus-ring cursor-pointer transition-colors hover:brightness-125"
                style={openConcept === c.concept ? { color: 'var(--text)', borderColor: 'var(--accent-primary)', background: 'var(--glass-bg-active)' } : undefined}
              >
                {c.concept}
              </button>
            ))}
          </div>
          <AnimatePresence mode="wait">
            {view.key_concepts.filter((c) => c.concept === openConcept).map((c) => (
              <motion.div key={c.concept} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                <p className="mt-3 text-sm">{c.explanation}</p>
                {c.relevance && <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>In this code: {c.relevance}</p>}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Section icon={<ShieldAlert size={14} aria-hidden />} title="Edge cases" items={view.edge_cases} />
        <Section icon={<Zap size={14} aria-hidden />} title="Optimisations" items={view.optimizations} />
      </div>
      <Section icon={<LinkIcon size={14} aria-hidden />} title="Related algorithms & patterns" items={view.related_algorithms} />
    </div>
  );
}
