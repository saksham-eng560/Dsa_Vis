/** Big-O helpers: colour coding, ranking and growth curves for the chart. */

export type ComplexityTone = 'green' | 'blue' | 'yellow' | 'orange' | 'red' | 'neutral';

interface Growth {
  rank: number;
  tone: ComplexityTone;
  fn: (n: number) => number;
}

/** Normalise notation variants: "O(n^2)" → "O(n²)", "O(nlogn)" → "O(n log n)". */
export function normalize(notation: string): string {
  return notation
    .replace(/\s+/g, ' ')
    .replace(/\^2|\*\*2/g, '²')
    .replace(/\^3|\*\*3/g, '³')
    .replace(/2\^n|2\*\*n/gi, '2ⁿ')
    .replace(/nlogn/gi, 'n log n')
    .replace(/\blg\b/g, 'log')
    .trim();
}

/** Classify a notation into a growth family. */
export function growth(notation: string): Growth {
  const n = normalize(notation).toLowerCase();
  if (/n!|factorial/.test(n)) return { rank: 8, tone: 'red', fn: (x) => factorial(x) };
  if (/[2-9]ⁿ|\^n|exp/.test(n)) return { rank: 7, tone: 'red', fn: (x) => 2 ** x };
  if (/n³|n\^3/.test(n)) return { rank: 6, tone: 'orange', fn: (x) => x ** 3 };
  if (/n²|n\^2|n \* m|nm|n\*m|v\s*\*\s*e/.test(n)) return { rank: 5, tone: 'orange', fn: (x) => x * x };
  if (/n log|v \+ e\) log|e log/.test(n)) return { rank: 4, tone: 'yellow', fn: (x) => x * Math.log2(Math.max(x, 1)) };
  if (/^o\(\s*log/.test(n)) return { rank: 2, tone: 'blue', fn: (x) => Math.log2(Math.max(x, 1)) };
  if (/\bn\b|v \+ e|n \+ m|\bm\b|\bk\b/.test(n)) return { rank: 3, tone: 'yellow', fn: (x) => x };
  if (/o\(1\)/.test(n)) return { rank: 1, tone: 'green', fn: () => 1 };
  return { rank: 0, tone: 'neutral', fn: (x) => x };
}

function factorial(x: number): number {
  let r = 1;
  for (let i = 2; i <= Math.round(x); i += 1) r *= i;
  return r;
}

/** Reference curves drawn behind the analysed complexity. */
export const REFERENCE_CURVES = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(2ⁿ)'] as const;

export const TONE_CLASSES: Record<ComplexityTone, string> = {
  green: 'tone-green',
  blue: 'tone-blue',
  yellow: 'tone-yellow',
  orange: 'tone-orange',
  red: 'tone-red',
  neutral: 'tone-neutral',
};
