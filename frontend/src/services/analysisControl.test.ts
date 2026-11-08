import { describe, expect, it } from 'vitest';

import { beginAnalysis, cancelAnalysis } from './analysisControl';

describe('analysis cancellation', () => {
  it('starting a new analysis aborts the previous one', () => {
    const first = beginAnalysis();
    const second = beginAnalysis();
    expect(first.aborted).toBe(true);
    expect(second.aborted).toBe(false);
    cancelAnalysis();
    expect(second.aborted).toBe(true);
  });
});
