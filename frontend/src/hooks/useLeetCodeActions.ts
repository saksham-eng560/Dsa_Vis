/**
 * LeetCode mode actions: load problems (restoring your saved code per problem),
 * run all test cases, and visualise one test case as a dry run.
 */
import { useCallback, useEffect } from 'react';

import { toast } from '../components/ui/Toast';
import { ApiError, fetchProblem, fetchProblemList, runTests } from '../services/api';
import { useAppStore } from '../stores/appStore';
import { useLeetCode } from '../stores/leetcodeStore';
import type { TestResult } from '../types/leetcode';
import { loadJSON, saveJSON } from '../utils/storage';
import { useAnalysis } from './useAnalysis';

const codeKey = (slug: string) => `codelens.lc.code.${slug}`;
const message = (err: unknown) => (err instanceof ApiError ? err.message : 'Something went wrong.');

/** Save the editor contents for the current problem (debounced). */
export function usePersistProblemCode(): void {
  const code = useAppStore((s) => s.code);
  const slug = useLeetCode((s) => (s.mode === 'leetcode' ? s.problem?.slug : undefined));
  useEffect(() => {
    if (!slug) return;
    const t = window.setTimeout(() => saveJSON(codeKey(slug), code), 400);
    return () => window.clearTimeout(t);
  }, [code, slug]);
}

export function useLeetCodeActions() {
  const { analyze } = useAnalysis();

  const loadCatalog = useCallback(async () => {
    if (useLeetCode.getState().catalog.length) return;
    try {
      useLeetCode.getState().setCatalog(await fetchProblemList());
    } catch {
      /* the picker still accepts any number / name */
    }
  }, []);

  const loadProblem = useCallback(async (ref: string) => {
    if (!ref.trim()) return;
    const lc = useLeetCode.getState();
    lc.setLoading(true);
    try {
      const problem = await fetchProblem(ref);
      lc.setProblem(problem);
      const app = useAppStore.getState();
      app.setCode(loadJSON<string>(codeKey(problem.slug), '') || problem.starter_code);
      app.setLanguage('python');
      app.clearResult();
      app.setTab('problem');
    } catch (err) {
      lc.setLoading(false, message(err));
    }
  }, []);

  const resetToStarter = useCallback(() => {
    const problem = useLeetCode.getState().problem;
    if (problem) useAppStore.getState().setCode(problem.starter_code);
  }, []);

  const runAll = useCallback(async () => {
    const lc = useLeetCode.getState();
    const { code, setTab } = useAppStore.getState();
    if (!lc.problem || !lc.tests.length) return;
    lc.startRun();
    setTab('problem');
    try {
      const res = await runTests(
        code,
        lc.problem.slug,
        lc.tests.map((t) => ({ input: t.input, expected: t.expected.trim() || null })),
        lc.compare,
      );
      const byId: Record<string, TestResult> = {};
      lc.tests.forEach((t, i) => {
        const r = res.results[i];
        if (r) byId[t.id] = r;
      });
      useLeetCode.getState().finishRun(byId, res.error);
      if (!res.error) toast(res.passed === res.total ? 'success' : 'info', `${res.passed} / ${res.total} tests passed`);
    } catch (err) {
      useLeetCode.getState().finishRun({}, message(err));
    }
  }, []);

  const visualize = useCallback(
    async (testId: string) => {
      useLeetCode.getState().setActiveTest(testId);
      useAppStore.getState().setTab('dryrun');
      await analyze();
    },
    [analyze],
  );

  return { loadCatalog, loadProblem, resetToStarter, runAll, visualize };
}
