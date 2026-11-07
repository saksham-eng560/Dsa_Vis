/** LeetCode mode contract — mirrors `backend/api/schemas/leetcode.py`. */

export type CompareMode = 'exact' | 'unordered' | 'unordered_nested';
export type TestStatus = 'passed' | 'failed' | 'error' | 'timeout' | 'ran';

export interface LCParam {
  name: string;
  type: string;
}

export interface LCSummary {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
}

export interface LCProblem extends LCSummary {
  tags: string[];
  description: string;
  function_name: string | null;
  params: LCParam[];
  return_type: string;
  output_param: number | null;
  design: boolean;
  class_name: string | null;
  starter_code: string;
  examples: { input: string[]; expected: string | null }[];
  compare: CompareMode;
  source: 'bundled' | 'leetcode';
  url: string;
}

/** A test case in the editor (examples are seeded from the problem). */
export interface TestCase {
  id: string;
  origin: 'example' | 'custom';
  input: string[];
  expected: string;
}

export interface TestResult {
  status: TestStatus;
  label: string;
  output: string | null;
  expected: string | null;
  error: string | null;
  stdout: string;
  ms: number;
}

export interface RunTestsResponse {
  results: TestResult[];
  passed: number;
  total: number;
  compare: CompareMode;
  error: string | null;
}
