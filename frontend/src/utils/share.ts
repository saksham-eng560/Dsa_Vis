/** Share links: the editor state is encoded (UTF-8 → base64url) in the URL hash. */
import type { LanguageChoice } from '../types';

export interface SharedState {
  code: string;
  language: LanguageChoice;
  entryCall?: string;
}

function toBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function fromBase64Url(encoded: string): string {
  const b64 = encoded.replace(/-/g, '+').replace(/_/g, '/');
  const binary = atob(b64 + '==='.slice((b64.length + 3) % 4));
  return new TextDecoder().decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
}

export function encodeShare(state: SharedState): string {
  return `#code=${toBase64Url(JSON.stringify(state))}`;
}

/** Decode `#code=…`; returns null for missing/corrupt hashes. */
export function decodeShare(hash: string): SharedState | null {
  const match = /#code=([\w-]+)/.exec(hash);
  if (!match?.[1]) return null;
  try {
    const parsed: unknown = JSON.parse(fromBase64Url(match[1]));
    if (parsed && typeof parsed === 'object' && typeof (parsed as SharedState).code === 'string') {
      return parsed as SharedState;
    }
  } catch {
    /* corrupt link */
  }
  return null;
}
