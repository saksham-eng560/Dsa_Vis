/**
 * Global UI state (Zustand). Server data lives in `result`; the dry-run cursor,
 * breakpoints and playback live here so the editor, flowchart and player stay
 * in sync without prop drilling.
 */
import { create } from 'zustand';

import type { AnalysisResult, HistoryItem, LanguageChoice, TabId } from '../types';
import { loadJSON, saveJSON } from '../utils/storage';

export type Status = 'idle' | 'analyzing' | 'done' | 'error';
export type Theme = 'dark' | 'light';

const HISTORY_KEY = 'codelens.history.v1';
const THEME_KEY = 'codelens.theme';
const MAX_HISTORY = 25;

interface AppState {
  code: string;
  language: LanguageChoice;
  entryCall: string;
  status: Status;
  stage: string;
  llmChars: number;
  result: AnalysisResult | null;
  error: string | null;
  activeTab: TabId;
  step: number; // 0-based index into result.dry_run.steps
  playing: boolean;
  speed: number;
  breakpoints: number[];
  history: HistoryItem[];
  sidebarOpen: boolean;
  theme: Theme;

  setCode: (code: string) => void;
  setLanguage: (language: LanguageChoice) => void;
  setEntryCall: (entryCall: string) => void;
  setTab: (tab: TabId) => void;
  setStep: (step: number) => void;
  setPlaying: (playing: boolean) => void;
  setSpeed: (speed: number) => void;
  toggleBreakpoint: (line: number) => void;
  setSidebar: (open: boolean) => void;
  toggleTheme: () => void;
  startAnalysis: () => void;
  setProgress: (stage: string, llmChars?: number) => void;
  setResult: (result: AnalysisResult, final: boolean) => void;
  fail: (message: string) => void;
  addHistory: (item: HistoryItem) => void;
  clearHistory: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  code: '',
  language: 'auto',
  entryCall: '',
  status: 'idle',
  stage: '',
  llmChars: 0,
  result: null,
  error: null,
  activeTab: 'flowchart',
  step: 0,
  playing: false,
  speed: 1,
  breakpoints: [],
  history: loadJSON<HistoryItem[]>(HISTORY_KEY, []),
  sidebarOpen: false,
  theme: loadJSON<Theme>(THEME_KEY, 'dark'),

  setCode: (code) => set({ code }),
  setLanguage: (language) => set({ language }),
  setEntryCall: (entryCall) => set({ entryCall }),
  setTab: (activeTab) => set({ activeTab }),
  setStep: (step) => {
    const total = get().result?.dry_run.steps.length ?? 0;
    set({ step: Math.max(0, Math.min(step, Math.max(total - 1, 0))) });
  },
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  toggleBreakpoint: (line) =>
    set(({ breakpoints }) => ({
      breakpoints: breakpoints.includes(line) ? breakpoints.filter((l) => l !== line) : [...breakpoints, line],
    })),
  setSidebar: (sidebarOpen) => set({ sidebarOpen }),
  toggleTheme: () => {
    const theme: Theme = get().theme === 'dark' ? 'light' : 'dark';
    saveJSON(THEME_KEY, theme);
    set({ theme });
  },
  startAnalysis: () => set({ status: 'analyzing', stage: 'Starting…', llmChars: 0, error: null, playing: false }),
  setProgress: (stage, llmChars) => set((s) => ({ stage, llmChars: llmChars ?? s.llmChars })),
  setResult: (result, final) =>
    set((s) => ({
      result,
      status: final ? 'done' : s.status,
      // keep the cursor when the LLM refines a partial result with the same trace
      step: s.result && s.result.dry_run.steps.length === result.dry_run.steps.length ? s.step : 0,
    })),
  fail: (error) => set({ status: 'error', error, playing: false }),
  addHistory: (item) =>
    set(({ history }) => {
      const next = [item, ...history.filter((h) => h.code !== item.code)].slice(0, MAX_HISTORY);
      saveJSON(HISTORY_KEY, next);
      return { history: next };
    }),
  clearHistory: () => {
    saveJSON(HISTORY_KEY, []);
    set({ history: [] });
  },
}));

/** Convenience selector for the current dry-run step. */
export const useCurrentStep = () =>
  useAppStore((s) => s.result?.dry_run.steps[s.step]);
