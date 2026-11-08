/**
 * Problem search (combobox): type a number, title words, slug or URL.
 * Bundled problems match instantly; leetcode.com is searched live. Enter loads
 * the highlighted suggestion, or the typed text as-is (e.g. "887").
 */
import { Loader2, RotateCcw, Search } from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';

import { useLeetCodeActions } from '../../hooks/useLeetCodeActions';
import { useProblemSearch } from '../../hooks/useProblemSearch';
import { useLeetCode } from '../../stores/leetcodeStore';
import type { LCSummary } from '../../types/leetcode';
import { GlowButton } from '../ui/GlowButton';
import { DifficultyBadge } from './DifficultyBadge';

export function ProblemPicker() {
  const { loadCatalog, loadProblem, resetToStarter } = useLeetCodeActions();
  const problem = useLeetCode((s) => s.problem);
  const loading = useLeetCode((s) => s.loading);
  const error = useLeetCode((s) => s.error);
  const language = useLeetCode((s) => s.language);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const { results, searching } = useProblemSearch(query);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);
  useEffect(() => setHighlight(-1), [query]);
  useEffect(() => {
    const close = (e: MouseEvent) => !boxRef.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const choose = (ref: string, label?: string) => {
    setOpen(false);
    setQuery(label ?? ref);
    void loadProblem(ref);
  };
  const pick = (p: LCSummary) => choose(p.slug, `${p.id}. ${p.title}`);

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      setOpen(true);
      const delta = e.key === 'ArrowDown' ? 1 : -1;
      setHighlight((h) => (results.length ? (h + delta + results.length) % results.length : -1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const chosen = results[highlight];
      if (open && chosen) pick(chosen);
      else if (query.trim()) choose(query.trim());
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div ref={boxRef} className="relative flex gap-2">
        <div className="relative flex-1">
          <Search size={16} aria-hidden className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-faint)' }} />
          <input
            role="combobox"
            aria-expanded={open}
            aria-controls="problem-suggestions"
            aria-activedescendant={highlight >= 0 ? `problem-opt-${highlight}` : undefined}
            aria-label="Search LeetCode problems by number, name or URL"
            className="field w-full pl-10 pr-9"
            placeholder="Search problems — 887, two sum, or a LeetCode link"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKey}
            spellCheck={false}
            autoComplete="off"
          />
          {(searching || loading) && (
            <Loader2 size={15} aria-hidden className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin" style={{ color: 'var(--text-faint)' }} />
          )}
          {open && (results.length > 0 || query.trim()) && (
            <ul
              id="problem-suggestions"
              role="listbox"
              className="glass-strong absolute left-0 right-0 top-[calc(100%+6px)] z-30 max-h-80 overflow-y-auto rounded-xl p-1 shadow-2xl scroll-thin"
              style={{ background: 'var(--surface-solid)', border: '1px solid var(--glass-border-hover)' }}
            >
              {!query.trim() && (
                <li className="px-3 pb-1 pt-2 text-[0.68rem] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
                  Popular problems
                </li>
              )}
              {results.map((p, i) => (
                <li
                  key={p.slug}
                  id={`problem-opt-${i}`}
                  role="option"
                  aria-selected={i === highlight}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pick(p)}
                  onMouseEnter={() => setHighlight(i)}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm"
                  style={i === highlight ? { background: 'var(--glass-bg-active)' } : undefined}
                >
                  <span className="w-12 shrink-0 font-mono text-xs" style={{ color: 'var(--text-faint)' }}>#{p.id}</span>
                  <span className="min-w-0 flex-1 truncate">{p.title}</span>
                  <DifficultyBadge difficulty={p.difficulty} />
                </li>
              ))}
              {query.trim() && !results.length && !searching && (
                <li className="px-3 py-2 text-sm" style={{ color: 'var(--text-muted)' }}>
                  No suggestions — press <kbd className="chip !py-0">Enter</kbd> to load “{query.trim()}” directly.
                </li>
              )}
            </ul>
          )}
        </div>
        <GlowButton onClick={() => query.trim() && choose(query.trim())} disabled={loading || !query.trim()}>
          {loading ? 'Loading…' : 'Load'}
        </GlowButton>
      </div>
      {error && (
        <p role="alert" className="text-xs" style={{ color: 'var(--accent-danger)' }}>
          {error}
        </p>
      )}
      {problem && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-semibold">
            {problem.id}. {problem.title}
          </span>
          <DifficultyBadge difficulty={problem.difficulty} />
          <code className="chip font-mono">
            {problem.design ? `class ${problem.class_name}` : `${problem.function_name}(${problem.params.map((p) => p.name).join(', ')})`}
          </code>
          <button
            className="chip focus-ring ml-auto cursor-pointer"
            onClick={resetToStarter}
            title={`Replace the editor contents with the ${language === 'cpp' ? 'C++' : 'Python'} starter code`}
          >
            <RotateCcw size={12} aria-hidden /> Starter code
          </button>
        </div>
      )}
    </div>
  );
}
