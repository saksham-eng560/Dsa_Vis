/**
 * Explain tab — a structured lesson about the user's code:
 * summary → intuition → how it works (line-linked steps) → why it works →
 * walkthrough on the real input → complexity in words → concepts, edge cases,
 * optimisations, common mistakes, related patterns → a chat box for doubts.
 * "Explain like I'm 5" swaps in a simpler version of the same structure.
 */
import { AnimatePresence, motion } from 'framer-motion';
import { Baby, CheckCircle2, Gauge, Lightbulb, Link as LinkIcon, ListOrdered, OctagonAlert, ShieldAlert, Sparkles, Zap } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';

import { explain } from '../../services/api';
import { useAppStore } from '../../stores/appStore';
import type { AnalysisResult, Explanation } from '../../types';
import { InlineChat } from '../chat/InlineChat';
import { LineRefText } from '../explain/LineRefText';
import { Walkthrough } from '../explain/Walkthrough';
import { TypewriterText } from '../shared/TypewriterText';
import { toast } from '../ui/Toast';
import { ComplexityBadge } from './ComplexityCard';

function Heading({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
      {icon} {children}
    </h3>
  );
}

function ListSection({ icon, title, items, tone }: { icon: ReactNode; title: string; items: string[]; tone?: string }) {
  if (!items.length) return null;
  return (
    <section className="glass-inset p-4">
      <Heading icon={icon}>{title}</Heading>
      <motion.ul className="space-y-2 text-sm leading-relaxed" initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.05 } } }}>
        {items.map((item) => (
          <motion.li key={item} variants={{ hidden: { opacity: 0, x: -6 }, show: { opacity: 1, x: 0 } }} className="flex gap-2" style={{ color: 'var(--text-muted)' }}>
            <span style={{ color: tone ?? 'var(--accent-primary)' }}>•</span>
            <span><LineRefText text={item} /></span>
          </motion.li>
        ))}
      </motion.ul>
    </section>
  );
}

export function ExplanationPanel({ result }: { result: AnalysisResult }) {
  const [eli5, setEli5] = useState(false);
  const [simple, setSimple] = useState<Explanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [openConcept, setOpenConcept] = useState<string | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const refining = useAppStore((s) => s.status === 'analyzing');

  useEffect(() => {
    setSimple(null);
    setEli5(false);
  }, [result.summary]);

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
  const cx = result.complexity;
  return (
    <div className="flex flex-col gap-4">
      <section className="glass-inset p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold">{view.algorithm_name}</h3>
          {refining && !result.llm_used && (
            <span className="chip animate-pulse"><Sparkles size={11} aria-hidden /> AI explanation on the way…</span>
          )}
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
          <TypewriterText key={`${eli5}-${view.summary}`} text={view.summary} className="text-[0.95rem] leading-relaxed">
            <LineRefText text={view.summary} />
          </TypewriterText>
        )}
        {view.intuition && (
          <div className="mt-4 flex gap-3 rounded-xl p-3" style={{ background: 'color-mix(in srgb, var(--accent-warning) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-warning) 30%, transparent)' }}>
            <Lightbulb size={18} aria-hidden className="mt-0.5 shrink-0" style={{ color: 'var(--accent-warning)' }} />
            <p className="text-sm leading-relaxed"><span className="font-semibold">Intuition: </span><LineRefText text={view.intuition} /></p>
          </div>
        )}
      </section>

      {view.approach.length > 0 && (
        <section className="glass-inset p-4">
          <Heading icon={<ListOrdered size={14} aria-hidden />}>How it works</Heading>
          <ol className="space-y-2.5">
            {view.approach.map((step, i) => (
              <motion.li key={step} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="flex gap-3 text-sm leading-relaxed">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold" style={{ background: 'color-mix(in srgb, var(--accent-primary) 25%, transparent)', color: 'var(--accent-primary)' }}>
                  {i + 1}
                </span>
                <span><LineRefText text={step} /></span>
              </motion.li>
            ))}
          </ol>
          {view.why_it_works && (
            <p className="mt-4 flex gap-2 rounded-xl p-3 text-sm leading-relaxed" style={{ background: 'var(--glass-bg)' }}>
              <CheckCircle2 size={16} aria-hidden className="mt-0.5 shrink-0" style={{ color: 'var(--accent-secondary)' }} />
              <span><span className="font-semibold">Why it works: </span><LineRefText text={view.why_it_works} /></span>
            </p>
          )}
        </section>
      )}

      <Walkthrough run={result.dry_run} />

      <section className="glass-inset p-4">
        <Heading icon={<Gauge size={14} aria-hidden />}>Complexity in plain words</Heading>
        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
          time <ComplexityBadge notation={cx.time.worst} /> · space <ComplexityBadge notation={cx.space.complexity} />
        </div>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}><LineRefText text={cx.time.explanation} /></p>
        {cx.space.explanation && <p className="mt-1 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}><LineRefText text={cx.space.explanation} /></p>}
      </section>

      {view.key_concepts.length > 0 && (
        <section className="glass-inset p-4">
          <Heading icon={<Lightbulb size={14} aria-hidden />}>Key concepts</Heading>
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
                {c.relevance && <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>In your code: <LineRefText text={c.relevance} /></p>}
              </motion.div>
            ))}
          </AnimatePresence>
          {!openConcept && <p className="mt-2 text-xs" style={{ color: 'var(--text-faint)' }}>Tap a concept to see what it means and where your code uses it.</p>}
        </section>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <ListSection icon={<ShieldAlert size={14} aria-hidden />} title="Edge cases" items={view.edge_cases} />
        <ListSection icon={<OctagonAlert size={14} aria-hidden />} title="Common mistakes" items={view.common_mistakes} tone="var(--accent-danger)" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <ListSection icon={<Zap size={14} aria-hidden />} title="Optimisations" items={view.optimizations} tone="var(--accent-secondary)" />
        <ListSection icon={<LinkIcon size={14} aria-hidden />} title="Related algorithms & patterns" items={view.related_algorithms} />
      </div>

      <InlineChat />
    </div>
  );
}
