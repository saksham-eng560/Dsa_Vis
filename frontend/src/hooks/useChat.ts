/**
 * Send a question to the tutor with automatic context: the code, the LeetCode
 * problem, the current dry-run step (line, variables), complexity and the
 * latest test results — so "why did cnt change here?" just works.
 */
import { useCallback, useRef } from 'react';

import { ApiError, chatStream } from '../services/api';
import { useAppStore } from '../stores/appStore';
import { useChat } from '../stores/chatStore';
import { useLeetCode } from '../stores/leetcodeStore';

function buildContext(): string {
  const app = useAppStore.getState();
  const lc = useLeetCode.getState();
  const parts: string[] = [];
  const r = app.result;
  if (r) {
    parts.push(`Analysis: ${r.algorithm_name}; time ${r.complexity.time.worst} worst, space ${r.complexity.space.complexity}.`);
    const step = r.dry_run.steps[app.step];
    if (step) {
      const vars = Object.entries(step.variables).slice(0, 12).map(([k, v]) => `${k} = ${v.slice(0, 80)}`).join(', ');
      parts.push(`Dry run (${r.dry_run.input_example || 'sample input'}), step ${step.step}/${r.dry_run.steps.length} at line ${step.line}: ${step.description}\nVariables: ${vars}`);
    }
  }
  if (lc.mode === 'leetcode') {
    const failing = lc.tests
      .map((t, i) => ({ t, r: lc.results[t.id], i }))
      .filter(({ r: res }) => res && res.status !== 'passed')
      .slice(0, 3)
      .map(({ t, r: res, i }) => `Test ${i + 1} (${t.input.join(', ')}): ${res?.status} — output ${res?.output ?? '-'}, expected ${t.expected || '-'} ${res?.error ?? ''}`);
    if (failing.length) parts.push(`Failing tests:\n${failing.join('\n')}`);
    if (lc.runError) parts.push(`Run error: ${lc.runError.slice(0, 600)}`);
  }
  return parts.join('\n\n');
}

export function useChatActions() {
  const ctrl = useRef<AbortController | null>(null);

  const send = useCallback(async (question: string) => {
    const q = question.trim();
    const chat = useChat.getState();
    if (!q || chat.streaming) return;
    const app = useAppStore.getState();
    const lc = useLeetCode.getState();
    chat.push({ role: 'user', content: q });
    chat.push({ role: 'assistant', content: '' });
    chat.setStreaming(true);
    ctrl.current = new AbortController();
    const lcMode = lc.mode === 'leetcode';
    try {
      const history = useChat.getState().messages.slice(0, -1);
      for await (const ev of chatStream(
        {
          messages: history,
          code: app.code,
          language: lcMode ? lc.language : (app.result?.language ?? app.language),
          problem: lcMode ? (lc.problem?.slug ?? null) : null,
          context: buildContext(),
        },
        ctrl.current.signal,
      )) {
        if (ev.text) useChat.getState().appendToLast(ev.text);
        if (ev.error) {
          useChat.getState().appendToLast(ev.error);
          useChat.getState().setStreaming(false, ev.error);
          return;
        }
      }
      useChat.getState().setStreaming(false);
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        useChat.getState().setStreaming(false);
        return;
      }
      const msg = err instanceof ApiError ? err.message : 'Something went wrong.';
      useChat.getState().appendToLast(msg);
      useChat.getState().setStreaming(false, msg);
    }
  }, []);

  const stop = useCallback(() => ctrl.current?.abort(), []);
  return { send, stop };
}
