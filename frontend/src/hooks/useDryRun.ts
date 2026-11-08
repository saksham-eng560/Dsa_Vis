/**
 * Dry-run playback: advances the shared step cursor on a timer scaled by
 * `speed`, pausing at breakpoints and at the end. Also wires ←/→/space keys.
 */
import { useEffect } from 'react';

import { useAppStore } from '../stores/appStore';

const BASE_INTERVAL_MS = 900;

export function useDryRunPlayback(): void {
  const playing = useAppStore((s) => s.playing);
  const speed = useAppStore((s) => s.speed);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      const { step, result, breakpoints, setStep, setPlaying } = useAppStore.getState();
      const steps = result?.dry_run.steps ?? [];
      if (step >= steps.length - 1) {
        setPlaying(false);
        return;
      }
      const next = step + 1;
      setStep(next);
      const line = steps[next]?.line;
      if (line != null && breakpoints.includes(line)) setPlaying(false);
    }, BASE_INTERVAL_MS / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed]);
}

/** Keyboard shortcuts active while the Dry Run tab is visible. */
export function useDryRunKeys(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target?.closest('.monaco-editor, input, textarea, select')) return;
      const { step, setStep, playing, setPlaying } = useAppStore.getState();
      if (e.key === 'ArrowRight') setStep(step + 1);
      else if (e.key === 'ArrowLeft') setStep(step - 1);
      else if (e.key === ' ') setPlaying(!playing);
      else return;
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled]);
}
