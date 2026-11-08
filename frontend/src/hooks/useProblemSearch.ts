/** Problem suggestions: instant matches from the bundled list, then live LeetCode search (debounced). */
import { useEffect, useMemo, useState } from 'react';

import { searchProblems } from '../services/api';
import { useLeetCode } from '../stores/leetcodeStore';
import type { LCSummary } from '../types/leetcode';

const DEBOUNCE_MS = 250;

/** Rank bundled problems: exact number, number prefix, title prefix, title/slug contains. */
export function filterCatalog(catalog: LCSummary[], query: string): LCSummary[] {
  const q = query.trim().toLowerCase();
  if (!q) return catalog;
  const score = (p: LCSummary) =>
    p.id === q ? 0 : p.id.startsWith(q) ? 1 : p.title.toLowerCase().startsWith(q) ? 2 : 3;
  return catalog
    .filter((p) => p.id.startsWith(q) || p.title.toLowerCase().includes(q) || p.slug.includes(q.replace(/\s+/g, '-')))
    .sort((a, b) => score(a) - score(b) || Number(a.id) - Number(b.id));
}

export function useProblemSearch(query: string): { results: LCSummary[]; searching: boolean } {
  const catalog = useLeetCode((s) => s.catalog);
  const local = useMemo(() => filterCatalog(catalog, query), [catalog, query]);
  const [remote, setRemote] = useState<LCSummary[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const q = query.trim();
    setRemote([]);
    if (!q) return;
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      searchProblems(q, ctrl.signal)
        .then(setRemote)
        .catch(() => setRemote([]))
        .finally(() => setSearching(false));
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
      setSearching(false);
    };
  }, [query]);

  const results = useMemo(() => {
    const seen = new Set<string>();
    return [...local, ...remote].filter((p) => !seen.has(p.slug) && seen.add(p.slug)).slice(0, 12);
  }, [local, remote]);
  return { results, searching };
}
