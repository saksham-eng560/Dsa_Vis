/**
 * Left pane: toolbar + Monaco (lazy) + optional entry-call input.
 * Supports drag-and-drop file upload and Ctrl/⌘+Enter to analyze.
 */
import { Play } from 'lucide-react';
import { lazy, Suspense, useDeferredValue, useEffect, useMemo, useState, type DragEvent } from 'react';

import { useAnalysis } from '../../hooks/useAnalysis';
import { usePersistProblemCode } from '../../hooks/useLeetCodeActions';
import { useLeetCode } from '../../stores/leetcodeStore';
import { ModeToggle } from '../leetcode/ModeToggle';
import { ProblemPicker } from '../leetcode/ProblemPicker';
import { useShareLink } from '../../hooks/useShareLink';
import { useAppStore } from '../../stores/appStore';
import { detectLanguage, languageFromFilename } from '../../utils/codeDetection';
import { GlassCard } from '../ui/GlassCard';
import { toast } from '../ui/Toast';
import { EditorToolbar } from './EditorToolbar';

const CodeEditor = lazy(() => import('./CodeEditor'));
const MAX_FILE_BYTES = 200_000;

export function EditorPanel() {
  const { analyze } = useAnalysis();
  const code = useAppStore((s) => s.code);
  const language = useAppStore((s) => s.language);
  const entryCall = useAppStore((s) => s.entryCall);
  const setEntryCall = useAppStore((s) => s.setEntryCall);
  const deferredCode = useDeferredValue(code); // debounce detection while typing
  const detected = useMemo(() => detectLanguage(deferredCode), [deferredCode]);
  const lcMode = useLeetCode((s) => s.mode === 'leetcode');
  const lcLanguage = useLeetCode((s) => s.language);
  const effective = lcMode ? lcLanguage : language === 'auto' ? detected : language;
  usePersistProblemCode();
  const [dragging, setDragging] = useState(false);

  const share = useShareLink(() => void analyze());

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        void analyze();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [analyze]);

  const loadFile = async (file: File) => {
    if (file.size > MAX_FILE_BYTES) {
      toast('error', 'That file is too large (max 200 KB).');
      return;
    }
    const { setCode, setLanguage } = useAppStore.getState();
    setCode((await file.text()).replace(/\r\n/g, '\n'));
    setLanguage(languageFromFilename(file.name) ?? 'auto');
    toast('success', `Loaded ${file.name}`);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) void loadFile(file);
  };

  return (
    <GlassCard className="flex min-h-[420px] flex-1 flex-col gap-3 p-4" aria-label="Code input">
      <ModeToggle />
      {lcMode && <ProblemPicker />}
      <EditorToolbar
        detected={detected}
        onAnalyze={() => void analyze()}
        onFile={(f) => void loadFile(f)}
        onShare={() => void share().then(() => toast('success', 'Share link copied to clipboard'))}
      />
      <div
        className="glass-inset relative min-h-0 flex-1 overflow-hidden"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <Suspense fallback={<div className="p-4 font-mono text-sm" style={{ color: 'var(--text-faint)' }}>Loading editor…</div>}>
          <CodeEditor language={effective} />
        </Suspense>
        {!code && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 text-center text-sm" style={{ color: 'var(--text-faint)' }}>
            <p className="text-base font-medium" style={{ color: 'var(--text-muted)' }}>
              {lcMode ? 'Load a LeetCode problem above' : 'Paste any code to visualise it'}
            </p>
            <p>{lcMode ? 'Its starter code appears here — write your Solution, then run the tests.' : '…or pick an example, or drop a file here.'}</p>
          </div>
        )}
        {dragging && (
          <div className="absolute inset-0 flex items-center justify-center text-sm font-medium" style={{ background: 'rgba(129,140,248,0.15)', border: '2px dashed var(--accent-primary)', borderRadius: 'inherit' }}>
            Drop to load file
          </div>
        )}
      </div>
      {effective === 'python' && !lcMode && (
        <label className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
          <Play size={14} aria-hidden />
          <span className="whitespace-nowrap">Dry-run call</span>
          <input
            className="field h-8 flex-1 font-mono"
            placeholder="optional, e.g. bubble_sort([4, 2, 7, 1]) — auto-generated if empty"
            value={entryCall}
            onChange={(e) => setEntryCall(e.target.value)}
            spellCheck={false}
          />
        </label>
      )}
    </GlassCard>
  );
}
