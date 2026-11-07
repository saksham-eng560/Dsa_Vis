/** Minimal, safe Markdown for tutor replies: code fences, inline code, bold, bullets (no raw HTML). */
import { Fragment, type ReactNode } from 'react';

function inline(text: string): ReactNode[] {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 1)
      return <code key={i} className="rounded px-1 font-mono text-[0.85em]" style={{ background: 'var(--glass-bg-active)' }}>{part.slice(1, -1)}</code>;
    if (part.startsWith('**') && part.endsWith('**') && part.length > 3) return <strong key={i}>{part.slice(2, -2)}</strong>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export function Markdown({ text }: { text: string }) {
  const blocks = text.split(/```(?:\w+)?\n?([\s\S]*?)(?:```|$)/g);
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {blocks.map((block, i) =>
        i % 2 === 1 ? (
          <pre key={i} className="overflow-x-auto rounded-lg p-3 font-mono text-xs scroll-thin" style={{ background: 'rgba(0,0,0,0.3)' }}>
            {block.replace(/\n$/, '')}
          </pre>
        ) : (
          block.split(/\n{2,}/).filter((p) => p.trim()).map((para, j) => {
            const lines = para.split('\n');
            if (lines.every((l) => /^\s*([-*•]|\d+\.)\s/.test(l) || !l.trim()))
              return (
                <ul key={`${i}-${j}`} className="list-disc space-y-1 pl-5">
                  {lines.filter((l) => l.trim()).map((l, k) => <li key={k}>{inline(l.replace(/^\s*([-*•]|\d+\.)\s/, ''))}</li>)}
                </ul>
              );
            return <p key={`${i}-${j}`} className="whitespace-pre-wrap">{inline(para.replace(/^#+\s*/, ''))}</p>;
          })
        ),
      )}
    </div>
  );
}
