/**
 * One shared cancellation handle for the streamed analysis. Starting a new
 * analysis — or switching problem/mode (clearResult) — aborts the previous
 * stream so a late result can never overwrite the current one.
 */
let current: AbortController | null = null;

export function beginAnalysis(): AbortSignal {
  current?.abort();
  current = new AbortController();
  return current.signal;
}

export function cancelAnalysis(): void {
  current?.abort();
  current = null;
}
