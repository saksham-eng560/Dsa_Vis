/**
 * Client-side language detection — a weighted keyword vote mirroring
 * `backend/core/code_parser.py`, used for instant editor feedback.
 */
import type { Language } from '../types';

const SIGNALS: Record<Language, [RegExp, number][]> = {
  python: [
    [/^\s*def \w+\(.*\)\s*(->\s*[\w[\], ]+)?:\s*$/gm, 5],
    [/^\s*(elif|except|finally)\b.*:\s*$/gm, 4],
    [/^\s*for \w+(, ?\w+)* in .+:\s*$/gm, 4],
    [/^\s*(import \w+|from [\w.]+ import)/gm, 2],
    [/\bprint\(/g, 1],
    [/\b(None|True|False|self)\b/g, 1],
  ],
  javascript: [
    [/\bfunction\s*\w*\s*\(/g, 3],
    [/\b(const|let|var)\s+\w+\s*=/g, 2],
    [/=>/g, 2],
    [/console\.log\(/g, 4],
    [/===|!==/g, 2],
  ],
  typescript: [
    [/\b(interface|type)\s+\w+\s*[={]/g, 4],
    [/\w+\s*:\s*(number|string|boolean|void|any)(\[\])?\b/g, 4],
    [/\bas\s+(number|string|const)\b/g, 2],
  ],
  cpp: [
    [/#include\s*</g, 6],
    [/\bstd::/g, 4],
    [/\b(cout|cin)\s*(<<|>>)/g, 4],
    [/\bvector</g, 3],
  ],
  java: [
    [/\bpublic\s+(static\s+)?(class|void|int)\b/g, 5],
    [/System\.out\.print/g, 6],
    [/\b(ArrayList|HashMap|String\[\])\b/g, 3],
  ],
  go: [
    [/^\s*package\s+\w+/gm, 6],
    [/\bfunc\s+(\(\w+ \*?\w+\)\s*)?\w+\(/g, 5],
    [/:=/g, 2],
    [/\bfmt\.Print/g, 4],
  ],
  rust: [
    [/\bfn\s+\w+\s*(<.*>)?\s*\(/g, 5],
    [/\blet\s+mut\b/g, 5],
    [/\b(println!|vec!)/g, 5],
    [/->\s*(i32|i64|usize|bool|Vec<)/g, 3],
  ],
};

/** Most likely language for `code` (python when nothing matches). */
export function detectLanguage(code: string): Language {
  const scores = Object.fromEntries(
    (Object.keys(SIGNALS) as Language[]).map((lang) => [
      lang,
      SIGNALS[lang].reduce((sum, [rx, w]) => sum + w * (code.match(rx)?.length ?? 0), 0),
    ]),
  ) as Record<Language, number>;
  if (scores.typescript > 0) scores.typescript += scores.javascript;
  let best: Language = 'python';
  for (const lang of Object.keys(scores) as Language[]) if (scores[lang] > scores[best]) best = lang;
  return best;
}

export const LANGUAGE_LABELS: Record<Language, string> = {
  python: 'Python',
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  cpp: 'C++',
  java: 'Java',
  go: 'Go',
  rust: 'Rust',
};

/** Monaco language ids differ for C++. */
export const monacoLanguage = (lang: Language): string => (lang === 'cpp' ? 'cpp' : lang);

/** Map an uploaded file extension to a language. */
export function languageFromFilename(name: string): Language | null {
  const ext = name.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, Language> = {
    py: 'python', js: 'javascript', mjs: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
    cpp: 'cpp', cc: 'cpp', cxx: 'cpp', hpp: 'cpp', h: 'cpp', c: 'cpp', java: 'java', go: 'go', rs: 'rust',
  };
  return map[ext] ?? null;
}
