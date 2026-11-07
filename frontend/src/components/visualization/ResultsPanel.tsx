/** Right pane: result header (algorithm, badges, warnings) + tabbed visualisations. */
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, BookOpen, Gauge, GitBranch, PlayCircle, Sparkles, Trophy } from 'lucide-react';
import { lazy, Suspense } from 'react';

import { useAppStore } from '../../stores/appStore';
import { useLeetCode } from '../../stores/leetcodeStore';
import { ProblemTab } from '../leetcode/ProblemTab';
import type { TabId } from '../../types';
import { LANGUAGE_LABELS } from '../../utils/codeDetection';
import { GlassCard } from '../ui/GlassCard';
import { LoadingOrb } from '../ui/LoadingOrb';
import { TabsPanel, type TabDef } from '../ui/TabsPanel';
import { ComplexityBadge, ComplexityCard } from './ComplexityCard';
import { DryRunTab } from './DryRunTab';
import { ExplanationPanel } from './ExplanationPanel';
import { WelcomeState } from './WelcomeState';

const FlowchartView = lazy(() => import('./FlowchartView'));

export function ResultsPanel() {
  const result = useAppStore((s) => s.result);
  const status = useAppStore((s) => s.status);
  const stage = useAppStore((s) => s.stage);
  const llmChars = useAppStore((s) => s.llmChars);
  const error = useAppStore((s) => s.error);
  const tab = useAppStore((s) => s.activeTab);
  const setTab = useAppStore((s) => s.setTab);
  const problem = useLeetCode((s) => (s.mode === 'leetcode' ? s.problem : null));

  const tabs: TabDef<TabId>[] = [
    ...(problem ? [{ id: 'problem' as const, label: 'Problem', icon: <Trophy size={15} aria-hidden /> }] : []),
    { id: 'flowchart', label: 'Flowchart', icon: <GitBranch size={15} aria-hidden /> },
    { id: 'dryrun', label: 'Dry Run', icon: <PlayCircle size={15} aria-hidden />, badge: result?.dry_run.steps.length || undefined },
    { id: 'complexity', label: 'Complexity', icon: <Gauge size={15} aria-hidden /> },
    { id: 'explain', label: 'Explain', icon: <BookOpen size={15} aria-hidden /> },
  ];

  const refining = status === 'analyzing' && result !== null;
  const activeTab = !problem && tab === 'problem' ? 'flowchart' : tab;
  const showTabs = result !== null || problem !== null;
  return (
    <GlassCard glow className="flex min-h-[560px] min-w-0 flex-col gap-3 p-4" aria-label="Analysis results">
      {error && status === 'error' && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm" style={{ borderColor: 'var(--accent-danger)', color: 'var(--accent-danger)', background: 'color-mix(in srgb, var(--accent-danger) 10%, transparent)' }}>
          <AlertTriangle size={16} aria-hidden /> {error}
        </div>
      )}
      {!showTabs && status === 'analyzing' && <LoadingOrb message={stage} chars={llmChars} />}
      {!showTabs && status !== 'analyzing' && <WelcomeState />}
      {showTabs && (
        <>
          {result && (
          <header className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold tracking-tight">{result.algorithm_name}</h2>
            <span className="chip">{LANGUAGE_LABELS[result.language]}</span>
            <ComplexityBadge notation={result.complexity.time.worst} />
            {result.data_structures_used.slice(0, 4).map((d) => (
              <span key={d} className="chip">{d}</span>
            ))}
            <span className="ml-auto flex items-center gap-2 text-xs" style={{ color: 'var(--text-faint)' }}>
              {refining ? (
                <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.6 }} className="flex items-center gap-1">
                  <Sparkles size={13} aria-hidden /> {stage}{llmChars ? ` · ${llmChars.toLocaleString()} chars` : ''}
                </motion.span>
              ) : result.llm_used ? (
                <span className="flex items-center gap-1"><Sparkles size={13} aria-hidden /> AI-enhanced</span>
              ) : (
                'static analysis'
              )}
            </span>
          </header>
          )}
          {result && result.warnings.length > 0 && (
            <ul className="space-y-1 text-xs" style={{ color: 'var(--accent-warning)' }}>
              {result.warnings.map((w) => (
                <li key={w} className="flex gap-1.5"><AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden /> {w}</li>
              ))}
            </ul>
          )}
          <TabsPanel tabs={tabs} active={activeTab} onChange={setTab} idPrefix="results" />
          <div className="min-h-0 flex-1">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                role="tabpanel"
                id={`results-panel-${activeTab}`}
                aria-labelledby={`results-tab-${activeTab}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                {activeTab === 'problem' && <ProblemTab />}
                {activeTab !== 'problem' && !result && (
                  status === 'analyzing' ? (
                    <LoadingOrb message={stage} chars={llmChars} />
                  ) : (
                    <p className="py-16 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                      Click <b>Visualize</b> on a test case (or the Visualize button) to trace your solution.
                    </p>
                  )
                )}
                {result && activeTab === 'flowchart' && (
                  <Suspense fallback={<LoadingOrb message="Loading diagram engine…" />}>
                    <FlowchartView chart={result.flowchart} />
                  </Suspense>
                )}
                {result && activeTab === 'dryrun' && <DryRunTab dryRun={result.dry_run} active />}
                {result && activeTab === 'complexity' && <ComplexityCard complexity={result.complexity} />}
                {result && activeTab === 'explain' && <ExplanationPanel result={result} />}
              </motion.div>
            </AnimatePresence>
          </div>
        </>
      )}
    </GlassCard>
  );
}
