/** Empty state before the first analysis: what CodeLens does + quick-start examples. */
import { motion } from 'framer-motion';
import { BookOpen, Gauge, GitBranch, PlayCircle } from 'lucide-react';

import { useAnalysis } from '../../hooks/useAnalysis';
import { useAppStore } from '../../stores/appStore';
import { PRESETS } from '../../utils/presets';

const FEATURES = [
  { icon: GitBranch, title: 'Flowcharts', text: 'Control flow of every function, laid out automatically.' },
  { icon: PlayCircle, title: 'Animated dry runs', text: 'Real execution traces with arrays, trees and graphs.' },
  { icon: Gauge, title: 'Big-O analysis', text: 'Best, average and worst case — with the reasoning.' },
  { icon: BookOpen, title: 'Plain English', text: 'What the code does, edge cases and improvements.' },
];

export function WelcomeState() {
  const { analyze } = useAnalysis();
  const quick = PRESETS.filter((p) => ['bubble', 'bfs', 'bst', 'lcs'].includes(p.id));
  return (
    <div className="flex h-full flex-col items-center justify-center gap-8 px-4 py-10 text-center">
      <div>
        <h2 className="bg-gradient-to-r from-indigo-300 via-violet-300 to-emerald-300 bg-clip-text text-3xl font-bold tracking-tight text-transparent md:text-4xl">
          See how your code thinks.
        </h2>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Paste any code — CodeLens traces it, draws it and explains it.
        </p>
      </div>
      <motion.div
        className="grid w-full max-w-xl grid-cols-1 gap-3 sm:grid-cols-2"
        initial="hidden"
        animate="show"
        variants={{ show: { transition: { staggerChildren: 0.08 } } }}
      >
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <motion.div key={title} variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }} className="glass-inset glass-hover p-4 text-left">
            <Icon size={18} aria-hidden style={{ color: 'var(--accent-primary)' }} />
            <p className="mt-2 text-sm font-semibold">{title}</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{text}</p>
          </motion.div>
        ))}
      </motion.div>
      <div className="flex flex-wrap justify-center gap-2">
        {quick.map((p) => (
          <button
            key={p.id}
            className="chip focus-ring glass-hover cursor-pointer !px-3 !py-1.5"
            onClick={() => {
              const { setCode, setLanguage, setEntryCall } = useAppStore.getState();
              setCode(p.code);
              setLanguage(p.language);
              setEntryCall(p.entryCall ?? '');
              void analyze();
            }}
          >
            Try {p.title}
          </button>
        ))}
      </div>
    </div>
  );
}
