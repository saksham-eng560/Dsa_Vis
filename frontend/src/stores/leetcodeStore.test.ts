import { beforeEach, describe, expect, it } from 'vitest';

import type { LCProblem } from '../types/leetcode';
import { activeTest, useLeetCode } from './leetcodeStore';

const problem: LCProblem = {
  id: '1', slug: 'two-sum', title: 'Two Sum', difficulty: 'Easy', tags: [], description: '',
  function_name: 'twoSum', params: [{ name: 'nums', type: 'integer[]' }, { name: 'target', type: 'integer' }],
  return_type: 'integer[]', output_param: null, design: false, class_name: null, starter_code: '', starter_code_cpp: '',
  examples: [{ input: ['[2,7]', '9'], expected: '[0,1]' }, { input: ['[3,3]', '6'], expected: null }],
  compare: 'unordered', source: 'bundled', url: '',
};

describe('leetcode store', () => {
  beforeEach(() => localStorage.clear());

  it('seeds tests from examples and activates the first', () => {
    useLeetCode.getState().setProblem(problem);
    const s = useLeetCode.getState();
    expect(s.tests.map((t) => [t.origin, t.input, t.expected])).toEqual([
      ['example', ['[2,7]', '9'], '[0,1]'],
      ['example', ['[3,3]', '6'], ''],
    ]);
    expect(activeTest(s)?.input).toEqual(['[2,7]', '9']);
  });

  it('remembers custom tests per problem and clears stale results on edit', () => {
    const lc = useLeetCode.getState();
    lc.setProblem(problem);
    lc.addTest();
    const custom = useLeetCode.getState().tests.at(-1)!;
    expect(custom.input).toEqual(['', '']); // one field per parameter
    useLeetCode.getState().finishRun({ [custom.id]: { status: 'passed', label: '', output: '1', expected: null, error: null, stdout: '', ms: 1 } }, null);
    useLeetCode.getState().updateTest(custom.id, { input: ['[1]', '1'] });
    expect(useLeetCode.getState().results[custom.id]).toBeUndefined();

    useLeetCode.getState().setProblem(problem); // reload → custom test restored
    const restored = useLeetCode.getState().tests.filter((t) => t.origin === 'custom');
    expect(restored.map((t) => t.input)).toEqual([['[1]', '1']]);
    useLeetCode.getState().removeTest(restored[0]!.id);
    useLeetCode.getState().setProblem(problem);
    expect(useLeetCode.getState().tests.some((t) => t.origin === 'custom')).toBe(false);
  });
});
