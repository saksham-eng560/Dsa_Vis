/**
 * Runs a streamed analysis: shows the static (partial) result immediately and
 * swaps in the LLM-enriched result when it arrives. Aborts in-flight requests
 * when a new analysis starts.
 */
import { useCallback, useRef } from 'react';

import { analyzeStream, ApiError } from '../services/api';
import { useAppStore } from '../stores/appStore';
import { activeTest, useLeetCode } from '../stores/leetcodeStore';
import type { AnalysisResult } from '../types';

export function useAnalysis() {
  const controller = useRef<AbortController | null>(null);

  const analyze = useCallback(async () => {
    const { code, language, entryCall, startAnalysis, setProgress, setResult, fail, addHistory } =
      useAppStore.getState();
    if (!code.trim()) {
      fail('Paste or type some code first.');
      return;
    }
    const lc = useLeetCode.getState();
    const lcMode = lc.mode === 'leetcode';
    if (lcMode && !lc.problem) {
      fail('Load a LeetCode problem first (enter its number or name above the editor).');
      return;
    }
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    startAnalysis();
    if (lcMode && useAppStore.getState().activeTab === 'problem') useAppStore.getState().setTab('dryrun');

    let final: AnalysisResult | null = null;
    try {
      const stream = analyzeStream(
        lcMode
          ? { code, language: lc.language, problem: lc.problem?.slug, test_input: activeTest(lc)?.input }
          : { code, language, entry_call: entryCall.trim() || null },
        ctrl.signal,
      );
      for await (const ev of stream) {
        if (ev.event === 'stage') setProgress(ev.data.message);
        else if (ev.event === 'token') setProgress(useAppStore.getState().stage, ev.data.chars);
        else if (ev.event === 'partial') setResult(ev.data, false);
        else if (ev.event === 'result') {
          final = ev.data;
          setResult(ev.data, true);
        } else if (ev.event === 'error') throw new ApiError(ev.data.detail, 500);
      }
      if (!final) throw new ApiError('The analysis ended unexpectedly. Please try again.', 500);
      addHistory({
        id: crypto.randomUUID(),
        createdAt: Date.now(),
        code,
        language,
        entryCall,
        title: final.algorithm_name !== 'Custom Logic' ? final.algorithm_name : firstLine(code),
        worst: final.complexity.time.worst,
      });
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      fail(err instanceof ApiError ? err.message : 'Something went wrong while analysing the code.');
    }
  }, []);

  const cancel = useCallback(() => controller.current?.abort(), []);
  return { analyze, cancel };
}

function firstLine(code: string): string {
  const line = code.split('\n').find((l) => l.trim()) ?? 'Snippet';
  return line.trim().slice(0, 40);
}
