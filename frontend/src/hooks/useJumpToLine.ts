/** Jump the dry run to the first step executing a given line (or to a step index). */
import { useCallback } from 'react';

import { useAppStore } from '../stores/appStore';

export function useJumpToLine() {
  const toLine = useCallback((line: number) => {
    const { result, setStep, setTab, step } = useAppStore.getState();
    const steps = result?.dry_run.steps ?? [];
    const after = steps.findIndex((s, i) => i > step && s.line === line);
    const idx = after >= 0 ? after : steps.findIndex((s) => s.line === line);
    if (idx >= 0) setStep(idx);
    setTab('dryrun');
  }, []);
  const toStep = useCallback((index: number) => {
    const { setStep, setTab } = useAppStore.getState();
    setStep(index);
    setTab('dryrun');
  }, []);
  return { toLine, toStep };
}
