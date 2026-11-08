/**
 * LeetCode mode actions: load problems (restoring your saved code per problem
 * and language), switch Python/C++, run all test cases, visualise one case.
 */
import { useCallback, useEffect } from 'react';

import { toast } from '../components/ui/Toast';
import { ApiError, fetchProblem, fetchProblemList, runTests } from '../services/api';
import { useAppStore } from '../stores/appStore';
import { useLeetCode } from '../stores/leetcodeStore';
import type { LCProblem, SolutionLanguage, TestResult } from '../types/leetcode';
import { loadJSON, saveJSON } from '../utils/storage';
import { useAnalysis } from './useAnalysis';

const codeKey = (slug: string, lang: SolutionLanguage) => `codelens.lc.code.${slug}${lang === 'cpp' ? '.cpp' : ''}`;
const message = (err: unknown) => (err instanceof ApiError ? err.message : 'Something went wrong.');
const CPP_FALLBACK = (p: LCProblem) =>
  p.design
    ? `class ${p.class_name ?? 'Solution'} {\npublic:\n    // write your solution here\n};\n`
    : `class Solution {\npublic:\n    // write ${p.function_name ?? 'your method'}(...) here\n};\n`;
/** Starter code for a language; C++ always gets at least an editable skeleton. */
const starter = (p: LCProblem, lang: SolutionLanguage) =>
  lang === 'cpp' ? p.starter_code_cpp || CPP_FALLBACK(p) : p.starter_code;

/** Save the editor contents for the current problem + language (debounced). */
export function usePersistProblemCode(): void {
  const code = useAppStore((s) => s.code);
  const slug = useLeetCode((s) => (s.mode === 'leetcode' ? s.problem?.slug : undefined));
  const language = useLeetCode((s) => s.language);
  useEffect(() => {
    if (!slug) return;
    const t = window.setTimeout(() => saveJSON(codeKey(slug, language), code), 400);
    return () => window.clearTimeout(t);
  }, [code, slug, language]);
}

/** Saved code for a problem in a language, or its starter code. */
function codeFor(problem: LCProblem, lang: SolutionLanguage): string {
  return loadJSON<string>(codeKey(problem.slug, lang), '') || starter(problem, lang);
}

export function useLeetCodeActions() {
  const { analyze } = useAnalysis();

  const loadCatalog = useCallback(async () => {
    if (useLeetCode.getState().catalog.length) return;
    try {
      useLeetCode.getState().setCatalog(await fetchProblemList());
    } catch {
      /* the search box still accepts any number / name */
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
      app.setCode(codeFor(problem, lc.language));
      app.setLanguage(lc.language);
      app.clearResult();
      app.setTab('problem');
      if (lc.language === 'cpp' && !problem.starter_code_cpp) {
        toast('info', 'No C++ template for this problem — a blank class was added. Running tests may need Python if it uses an unusual type.');
      }
    } catch (err) {
      lc.setLoading(false, message(err));
    }
  }, []);

  const switchLanguage = useCallback((lang: SolutionLanguage) => {
    const lc = useLeetCode.getState();
    if (lc.language === lang) return;
    const app = useAppStore.getState();
    if (lc.problem) saveJSON(codeKey(lc.problem.slug, lc.language), app.code);
    lc.setLanguage(lang);
    app.setLanguage(lang);
    app.clearResult();
    if (lc.problem) app.setCode(codeFor(lc.problem, lang));
  }, []);

  const resetToStarter = useCallback(() => {
    const { problem, language } = useLeetCode.getState();
    if (problem) useAppStore.getState().setCode(starter(problem, language));
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
        lc.language,
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

  return { loadCatalog, loadProblem, switchLanguage, resetToStarter, runAll, visualize };
}
