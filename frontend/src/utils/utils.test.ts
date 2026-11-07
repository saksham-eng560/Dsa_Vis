import { describe, expect, it } from 'vitest';

import { parseFrame } from '../services/api';
import type { FlowNode, Flowchart } from '../types';
import { detectLanguage, languageFromFilename } from './codeDetection';
import { growth, normalize } from './complexity';
import { flowGroups, groupForStep, nodeForLine, PROGRAM_GROUP, toMermaid } from './diagramHelpers';
import { decodeShare, encodeShare } from './share';

const node = (id: string, line: number | null, end: number | null, group = 'f', type: FlowNode['type'] = 'process'): FlowNode => ({
  id, type, label: id, line, end_line: end, group,
});

describe('detectLanguage', () => {
  it.each([
    ['def f(x):\n    for i in x:\n        print(i)', 'python'],
    ['function f(a) {\n  console.log(a);\n}', 'javascript'],
    ['function f(a: number): number {\n  return a;\n}', 'typescript'],
    ['#include <vector>\nint main() { std::cout << 1; }', 'cpp'],
    ['public class A { public static void main(String[] a) { System.out.println(1); } }', 'java'],
    ['package main\nfunc main() {\n  x := 1\n  fmt.Println(x)\n}', 'go'],
    ['fn main() {\n    let mut v = vec![1];\n}', 'rust'],
  ])('%#', (code, lang) => expect(detectLanguage(code)).toBe(lang));

  it('maps file extensions', () => {
    expect(languageFromFilename('a.rs')).toBe('rust');
    expect(languageFromFilename('README.md')).toBeNull();
  });
});

describe('complexity helpers', () => {
  it('normalises notation variants', () => {
    expect(normalize('O(n^2)')).toBe('O(n²)');
    expect(normalize('O(nlogn)')).toBe('O(n log n)');
  });
  it('orders growth families and colours them', () => {
    const ranks = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(2ⁿ)', 'O(n!)'].map((n) => growth(n).rank);
    expect([...ranks].sort((a, b) => a - b)).toEqual(ranks);
    expect(growth('O(1)').tone).toBe('green');
    expect(growth('O(log n)').tone).toBe('blue');
    expect(growth('O(n)').tone).toBe('yellow');
    expect(growth('O(n²)').tone).toBe('orange');
    expect(growth('O(2ⁿ)').tone).toBe('red');
    expect(growth('O(V + E)').rank).toBe(3);
  });
});

describe('share links', () => {
  it('round-trips unicode code', () => {
    const state = { code: 'print("héllo ✓")\n', language: 'python' as const, entryCall: 'f([1])' };
    expect(decodeShare(encodeShare(state))).toEqual(state);
  });
  it('rejects corrupt hashes', () => {
    expect(decodeShare('#code=!!!')).toBeNull();
    expect(decodeShare('')).toBeNull();
  });
});

describe('SSE frame parsing', () => {
  it('parses event + data', () => {
    expect(parseFrame('event: token\ndata: {"chars": 12}')).toEqual({ event: 'token', data: { chars: 12 } });
  });
  it('ignores frames without data or with bad JSON', () => {
    expect(parseFrame('event: ping')).toBeNull();
    expect(parseFrame('event: x\ndata: {oops')).toBeNull();
  });
});

describe('diagram helpers', () => {
  const nodes = [node('a', 1, 1, 'f', 'start'), node('b', 2, 4), node('c', 3, 3, 'f', 'decision'), node('d', null, null, 'f', 'end')];
  const chart: Flowchart = {
    nodes: [...nodes, node('m', 9, 9, PROGRAM_GROUP, 'start')],
    edges: [{ source: 'a', target: 'b', label: null }, { source: 'c', target: 'd', label: 'True' }],
    source: 'static',
  };

  it('maps lines to the tightest node', () => {
    expect(nodeForLine(nodes, 3)?.id).toBe('c');
    expect(nodeForLine(nodes, 4)?.id).toBe('b');
    expect(nodeForLine(nodes, 99)).toBeUndefined();
  });
  it('orders groups with the program last and resolves step groups', () => {
    const groups = flowGroups(chart);
    expect(groups).toEqual(['f', PROGRAM_GROUP]);
    const step = { function: '<module>' } as Parameters<typeof groupForStep>[0];
    expect(groupForStep(step, groups)).toBe(PROGRAM_GROUP);
  });
  it('exports Mermaid', () => {
    const text = toMermaid(chart, 'f');
    expect(text).toContain('flowchart TD');
    expect(text).toContain('c{"c"}');
    expect(text).toContain('c -->|True| d');
    expect(text).not.toContain('m([');
  });
});

describe('problem search ranking', async () => {
  const { filterCatalog } = await import('../hooks/useProblemSearch');
  const catalog = [
    { id: '1', slug: 'two-sum', title: 'Two Sum', difficulty: 'Easy' },
    { id: '15', slug: '3sum', title: '3Sum', difficulty: 'Medium' },
    { id: '167', slug: 'two-sum-ii', title: 'Two Sum II', difficulty: 'Medium' },
    { id: '206', slug: 'reverse-linked-list', title: 'Reverse Linked List', difficulty: 'Easy' },
  ];
  it('ranks exact number, then number prefix', () => {
    expect(filterCatalog(catalog, '1').map((p) => p.id)).toEqual(['1', '15', '167']);
  });
  it('matches title words and slugs', () => {
    expect(filterCatalog(catalog, 'two sum').map((p) => p.id)).toEqual(['1', '167']);
    expect(filterCatalog(catalog, 'linked').map((p) => p.id)).toEqual(['206']);
    expect(filterCatalog(catalog, '')).toHaveLength(4);
  });
});
