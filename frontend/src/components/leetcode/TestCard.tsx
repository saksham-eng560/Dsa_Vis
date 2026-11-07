/** One editable test case: inputs per parameter, expected output, latest result. */
import { motion } from 'framer-motion';
import { CheckCircle2, Clock, PlayCircle, Trash2, XCircle } from 'lucide-react';

import type { TestCase, TestResult, TestStatus } from '../../types/leetcode';

const STATUS: Record<TestStatus, { text: string; color: string }> = {
  passed: { text: 'Accepted', color: 'var(--accent-secondary)' },
  failed: { text: 'Wrong Answer', color: 'var(--accent-danger)' },
  error: { text: 'Runtime Error', color: 'var(--accent-danger)' },
  timeout: { text: 'Time Limit Exceeded', color: 'var(--accent-warning)' },
  ran: { text: 'Ran (no expected output)', color: 'var(--accent-blue)' },
};

interface TestCardProps {
  test: TestCase;
  title: string;
  paramNames: string[];
  result: TestResult | undefined;
  active: boolean;
  onChange: (patch: Partial<Pick<TestCase, 'input' | 'expected'>>) => void;
  onRemove: () => void;
  onVisualize: () => void;
}

const rows = (text: string) => Math.min(Math.max(text.split('\n').length, 1), 6);

export function TestCard({ test, title, paramNames, result, active, onChange, onRemove, onVisualize }: TestCardProps) {
  const compileError = result?.status === 'error' && /^(SyntaxError|IndentationError|TabError)/.test(result.error ?? '');
  const status = result ? (compileError ? { text: 'Compile Error', color: 'var(--accent-danger)' } : STATUS[result.status]) : null;
  const Icon = result?.status === 'passed' ? CheckCircle2 : result?.status === 'timeout' ? Clock : XCircle;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-inset flex flex-col gap-2 p-3"
      style={active ? { borderColor: 'var(--accent-primary)', boxShadow: '0 0 0 1px var(--accent-primary)' } : undefined}
      aria-label={title}
    >
      <header className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold">{title}</h4>
        {status && (
          <span className="flex items-center gap-1 text-xs font-semibold" style={{ color: status.color }}>
            <Icon size={14} aria-hidden /> {status.text}
          </span>
        )}
        {result && <span className="font-mono text-[0.68rem]" style={{ color: 'var(--text-faint)' }}>{result.ms} ms</span>}
        <span className="ml-auto flex gap-1.5">
          <button className="chip focus-ring cursor-pointer" onClick={onVisualize} title="Run the dry-run visualiser on this test case">
            <PlayCircle size={12} aria-hidden /> Visualize
          </button>
          {test.origin === 'custom' && (
            <button className="chip focus-ring cursor-pointer" onClick={onRemove} aria-label={`Delete ${title}`}>
              <Trash2 size={12} aria-hidden />
            </button>
          )}
        </span>
      </header>

      <div className="grid gap-2 sm:grid-cols-2">
        {paramNames.map((name, i) => (
          <label key={name} className="flex flex-col gap-1 text-[0.7rem]" style={{ color: 'var(--text-faint)' }}>
            <span className="font-mono">{name} =</span>
            <textarea
              className="field h-auto resize-y py-1.5 font-mono text-xs leading-5"
              rows={rows(test.input[i] ?? '')}
              value={test.input[i] ?? ''}
              placeholder={i === 0 ? 'e.g. [2,7,11,15]' : 'e.g. 9'}
              spellCheck={false}
              onChange={(e) => {
                const input = [...test.input];
                input[i] = e.target.value;
                onChange({ input });
              }}
            />
          </label>
        ))}
        <label className="flex flex-col gap-1 text-[0.7rem]" style={{ color: 'var(--text-faint)' }}>
          <span>Expected output (optional)</span>
          <textarea
            className="field h-auto resize-y py-1.5 font-mono text-xs leading-5"
            rows={rows(test.expected)}
            value={test.expected}
            placeholder="leave empty to just run"
            spellCheck={false}
            onChange={(e) => onChange({ expected: e.target.value })}
          />
        </label>
      </div>

      {result && (result.output !== null || result.error || result.stdout) && (
        <div className="grid gap-1 rounded-lg p-2 font-mono text-xs" style={{ background: 'var(--glass-bg)' }}>
          {result.output !== null && (
            <p>
              <span style={{ color: 'var(--text-faint)' }}>Output: </span>
              <span style={{ color: result.status === 'failed' ? 'var(--accent-danger)' : 'var(--text)' }}>{result.output}</span>
            </p>
          )}
          {result.status === 'failed' && result.expected && (
            <p>
              <span style={{ color: 'var(--text-faint)' }}>Expected: </span>
              <span style={{ color: 'var(--accent-secondary)' }}>{result.expected}</span>
            </p>
          )}
          {result.error && <p style={{ color: result.status === 'ran' ? 'var(--text-muted)' : 'var(--accent-danger)' }}>{result.error}</p>}
          {result.stdout && (
            <pre className="max-h-24 overflow-auto whitespace-pre-wrap scroll-thin" style={{ color: 'var(--text-muted)' }}>
              <span style={{ color: 'var(--text-faint)' }}>stdout: </span>
              {result.stdout}
            </pre>
          )}
        </div>
      )}
    </motion.article>
  );
}
