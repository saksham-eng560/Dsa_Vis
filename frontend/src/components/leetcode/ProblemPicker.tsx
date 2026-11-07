/**
 * Load a LeetCode problem by number, name, slug or URL — or pick a bundled one.
 * Bundled problems work offline; anything else is fetched from leetcode.com once.
 */
import { Download, RotateCcw, Search } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';

import { useLeetCodeActions } from '../../hooks/useLeetCodeActions';
import { useLeetCode } from '../../stores/leetcodeStore';
import { GlowButton } from '../ui/GlowButton';
import { DifficultyBadge } from './DifficultyBadge';

export function ProblemPicker() {
  const { loadCatalog, loadProblem, resetToStarter } = useLeetCodeActions();
  const catalog = useLeetCode((s) => s.catalog);
  const problem = useLeetCode((s) => s.problem);
  const loading = useLeetCode((s) => s.loading);
  const error = useLeetCode((s) => s.error);
  const [ref, setRef] = useState('');

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void loadProblem(ref);
  };

  return (
    <div className="flex flex-col gap-2">
      <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
        <label className="relative min-w-[12rem] flex-1">
          <span className="sr-only">LeetCode problem number, name or URL</span>
          <Search size={15} aria-hidden className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-faint)' }} />
          <input
            className="field w-full pl-9"
            placeholder="Problem # or name — e.g. 1, two-sum"
            title="LeetCode problem number, slug, title or URL"
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            spellCheck={false}
          />
        </label>
        <GlowButton type="submit" icon={<Download size={15} />} disabled={loading || !ref.trim()}>
          {loading ? 'Loading…' : 'Load'}
        </GlowButton>
        <select
          className="field max-w-[13rem] cursor-pointer"
          aria-label="Popular problems"
          value=""
          onChange={(e) => {
            setRef(e.target.value);
            void loadProblem(e.target.value);
          }}
        >
          <option value="" disabled>
            Popular problems…
          </option>
          {catalog.map((p) => (
            <option key={p.slug} value={p.slug}>
              {p.id}. {p.title} · {p.difficulty}
            </option>
          ))}
        </select>
      </form>
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
          <button className="chip focus-ring ml-auto cursor-pointer" onClick={resetToStarter} title="Replace the editor contents with the starter code">
            <RotateCcw size={12} aria-hidden /> Starter code
          </button>
        </div>
      )}
    </div>
  );
}
