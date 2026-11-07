/** Polls `/api/health` so the navbar can show backend + model status. */
import { useEffect, useState } from 'react';

import { fetchHealth } from '../services/api';
import type { HealthStatus } from '../types';

export type HealthState = { kind: 'loading' } | { kind: 'offline' } | { kind: 'online'; health: HealthStatus };

export function useHealth(intervalMs = 30_000): HealthState {
  const [state, setState] = useState<HealthState>({ kind: 'loading' });
  useEffect(() => {
    const ctrl = new AbortController();
    const check = () =>
      fetchHealth(ctrl.signal)
        .then((health) => setState({ kind: 'online', health }))
        .catch((err: Error) => err.name !== 'AbortError' && setState({ kind: 'offline' }));
    void check();
    const timer = window.setInterval(check, intervalMs);
    return () => {
      ctrl.abort();
      window.clearInterval(timer);
    };
  }, [intervalMs]);
  return state;
}
