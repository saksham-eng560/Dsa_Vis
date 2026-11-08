/** Pre-computed bubble-sort frames that drive the hero's live demo (code line ↔ bars). */
export interface DemoFrame {
  values: number[];
  line: number; // 1-based line in DEMO_CODE
  compare: [number, number] | null;
  swapped: boolean;
  sortedFrom: number; // indices >= sortedFrom are final
}

export const DEMO_CODE = [
  'def bubble_sort(arr):',
  '    n = len(arr)',
  '    for i in range(n):',
  '        for j in range(n - i - 1):',
  '            if arr[j] > arr[j + 1]:',
  '                arr[j], arr[j + 1] = arr[j + 1], arr[j]',
  '    return arr',
];

export function bubbleFrames(input: number[]): DemoFrame[] {
  const a = [...input];
  const n = a.length;
  const frames: DemoFrame[] = [{ values: [...a], line: 2, compare: null, swapped: false, sortedFrom: n }];
  for (let i = 0; i < n; i += 1) {
    for (let j = 0; j < n - i - 1; j += 1) {
      frames.push({ values: [...a], line: 5, compare: [j, j + 1], swapped: false, sortedFrom: n - i });
      if (a[j]! > a[j + 1]!) {
        [a[j], a[j + 1]] = [a[j + 1]!, a[j]!];
        frames.push({ values: [...a], line: 6, compare: [j, j + 1], swapped: true, sortedFrom: n - i });
      }
    }
  }
  frames.push({ values: [...a], line: 7, compare: null, swapped: false, sortedFrom: 0 });
  return frames;
}
