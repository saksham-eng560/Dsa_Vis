/**
 * LeetCode mode state: the loaded problem, editable test cases and their
 * latest results. Custom tests are remembered per problem in localStorage.
 */
import { create } from 'zustand';

import type { CompareMode, LCProblem, LCSummary, TestCase, TestResult } from '../types/leetcode';
import { loadJSON, saveJSON } from '../utils/storage';

export type Mode = 'free' | 'leetcode';

const MODE_KEY = 'codelens.mode';
const customKey = (slug: string) => `codelens.lc.tests.${slug}`;
const newId = () => crypto.randomUUID();

interface LeetCodeState {
  mode: Mode;
  catalog: LCSummary[];
  problem: LCProblem | null;
  loading: boolean;
  error: string | null;
  tests: TestCase[];
  activeTestId: string | null;
  results: Record<string, TestResult>;
  running: boolean;
  runError: string | null;
  compare: CompareMode | null; // null → problem default

  setMode: (mode: Mode) => void;
  setCatalog: (catalog: LCSummary[]) => void;
  setLoading: (loading: boolean, error?: string | null) => void;
  setProblem: (problem: LCProblem) => void;
  addTest: () => void;
  updateTest: (id: string, patch: Partial<Pick<TestCase, 'input' | 'expected'>>) => void;
  removeTest: (id: string) => void;
  setActiveTest: (id: string) => void;
  setCompare: (compare: CompareMode | null) => void;
  startRun: () => void;
  finishRun: (results: Record<string, TestResult>, error: string | null) => void;
}

/** Persist only user-made tests; examples always come from the problem. */
function persist(problem: LCProblem | null, tests: TestCase[]) {
  if (problem) saveJSON(customKey(problem.slug), tests.filter((t) => t.origin === 'custom'));
}

export const useLeetCode = create<LeetCodeState>((set, get) => ({
  mode: loadJSON<Mode>(MODE_KEY, 'free'),
  catalog: [],
  problem: null,
  loading: false,
  error: null,
  tests: [],
  activeTestId: null,
  results: {},
  running: false,
  runError: null,
  compare: null,

  setMode: (mode) => {
    saveJSON(MODE_KEY, mode);
    set({ mode });
  },
  setCatalog: (catalog) => set({ catalog }),
  setLoading: (loading, error = null) => set({ loading, error }),
  setProblem: (problem) => {
    const examples: TestCase[] = problem.examples.map((e) => ({
      id: newId(), origin: 'example', input: e.input, expected: e.expected ?? '',
    }));
    const custom = loadJSON<TestCase[]>(customKey(problem.slug), []);
    const tests = [...examples, ...custom];
    set({ problem, tests, activeTestId: tests[0]?.id ?? null, results: {}, runError: null, compare: null, loading: false, error: null });
  },
  addTest: () => {
    const { problem, tests } = get();
    const arity = problem?.design ? 2 : (problem?.params.length ?? 1);
    const test: TestCase = { id: newId(), origin: 'custom', input: Array.from({ length: arity }, () => ''), expected: '' };
    const next = [...tests, test];
    persist(problem, next);
    set({ tests: next, activeTestId: test.id });
  },
  updateTest: (id, patch) => {
    const next = get().tests.map((t) => (t.id === id ? { ...t, ...patch } : t));
    persist(get().problem, next);
    const results = { ...get().results };
    delete results[id]; // stale once edited
    set({ tests: next, results });
  },
  removeTest: (id) => {
    const next = get().tests.filter((t) => t.id !== id);
    persist(get().problem, next);
    set((s) => ({ tests: next, activeTestId: s.activeTestId === id ? (next[0]?.id ?? null) : s.activeTestId }));
  },
  setActiveTest: (activeTestId) => set({ activeTestId }),
  setCompare: (compare) => set({ compare }),
  startRun: () => set({ running: true, runError: null }),
  finishRun: (results, runError) => set({ running: false, results, runError }),
}));

/** The test case that drives the dry run. */
export const activeTest = (s: LeetCodeState) => s.tests.find((t) => t.id === s.activeTestId) ?? s.tests[0];
