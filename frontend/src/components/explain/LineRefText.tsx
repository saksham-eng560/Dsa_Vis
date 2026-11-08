/** Text where "Line 5" / "line 12" / "L7" become chips that jump the dry run to that line. */
import { Fragment } from 'react';

import { useJumpToLine } from '../../hooks/useJumpToLine';

const LINE_RX = /\b(?:[Ll]ines?\s+|L)(\d{1,4})(?:\s*[-–]\s*\d{1,4})?\b/g;

function Inline({ text }: { text: string }) {
  return (
    <>
      {text.split(/(`[^`]+`)/g).map((part, i) =>
        part.startsWith('`') && part.endsWith('`') && part.length > 1 ? (
          <code key={i} className="rounded px-1 font-mono text-[0.85em]" style={{ background: 'var(--glass-bg-active)' }}>
            {part.slice(1, -1)}
          </code>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}

export function LineRefText({ text }: { text: string }) {
  const { toLine } = useJumpToLine();
  const out = [];
  let last = 0;
  for (const m of text.matchAll(LINE_RX)) {
    const line = Number(m[1]);
    out.push(<Inline key={`t${last}`} text={text.slice(last, m.index)} />);
    out.push(
      <button
        key={`l${m.index}`}
        onClick={() => toLine(line)}
        className="mx-0.5 inline-flex items-center rounded-md px-1.5 py-px font-mono text-[0.8em] font-semibold transition-colors hover:brightness-125"
        style={{ background: 'color-mix(in srgb, var(--accent-primary) 22%, transparent)', color: 'var(--accent-primary)' }}
        title={`Show line ${line} in the dry run`}
      >
        {m[0]}
      </button>,
    );
    last = (m.index ?? 0) + m[0].length;
  }
  out.push(<Inline key="end" text={text.slice(last)} />);
  return <>{out}</>;
}
