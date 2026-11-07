/**
 * Thin typed client for the CodeLens API.
 * In dev, Vite proxies `/api` to FastAPI; set `VITE_API_URL` for other hosts.
 */
import type { AnalyzeRequest, Explanation, HealthStatus, StreamEvent } from '../types';
import type { CompareMode, LCProblem, LCSummary, RunTestsResponse, SolutionLanguage } from '../types/leetcode';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

/** Error carrying a user-presentable message. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/** Turn an HTTP failure into a friendly message (FastAPI `detail` aware). */
async function toError(res: Response): Promise<ApiError> {
  let detail = `Request failed (${res.status})`;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const d = (body as { detail: unknown }).detail;
      detail = typeof d === 'string' ? d : Array.isArray(d) ? 'The code could not be processed — is it empty?' : detail;
    }
  } catch {
    /* non-JSON body: keep generic message */
  }
  if (res.status === 429) detail = 'You are analysing very quickly — please wait a few seconds.';
  return new ApiError(detail, res.status);
}

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError('Cannot reach the CodeLens server. Is the backend running?', 0);
  }
  if (!res.ok) throw await toError(res);
  return (await res.json()) as T;
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { signal });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError('Cannot reach the CodeLens server. Is the backend running?', 0);
  }
  if (!res.ok) throw await toError(res);
  return (await res.json()) as T;
}

export const fetchHealth = (signal?: AbortSignal) => get<HealthStatus>('/api/health', signal);

export const fetchProblemList = () => get<LCSummary[]>('/api/leetcode/problems');

export const searchProblems = (q: string, signal?: AbortSignal) =>
  get<LCSummary[]>(`/api/leetcode/search?q=${encodeURIComponent(q)}`, signal);

export const fetchProblem = (ref: string) => get<LCProblem>(`/api/leetcode/problems/${encodeURIComponent(ref.trim())}`);

export function runTests(
  code: string,
  problem: string,
  tests: { input: string[]; expected: string | null }[],
  compare: CompareMode | null,
  language: SolutionLanguage,
) {
  return post<RunTestsResponse>('/api/leetcode/run', { code, problem, tests, compare, language });
}

export function explain(code: string, language: string, eli5: boolean, signal?: AbortSignal) {
  return post<Explanation>('/api/explain', { code, language, eli5 }, signal);
}

/** Parse one SSE frame (`event:` + `data:` lines). */
export function parseFrame(frame: string): StreamEvent | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join('\n')) } as StreamEvent;
  } catch {
    return null;
  }
}

/**
 * Stream analysis progress. Uses fetch + ReadableStream because EventSource
 * cannot POST a body.
 */
export async function* analyzeStream(req: AnalyzeRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/api/analyze/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError('Cannot reach the CodeLens server. Is the backend running?', 0);
  }
  if (!res.ok || !res.body) throw await toError(res);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let idx: number;
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const event = parseFrame(buffer.slice(0, idx));
      buffer = buffer.slice(idx + 2);
      if (event) yield event;
    }
  }
}
