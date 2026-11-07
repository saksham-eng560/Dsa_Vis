/** Python 3 / C++ switch for LeetCode mode. */
import { useLeetCodeActions } from '../../hooks/useLeetCodeActions';
import { useLeetCode } from '../../stores/leetcodeStore';
import type { SolutionLanguage } from '../../types/leetcode';

const OPTIONS: { id: SolutionLanguage; label: string }[] = [
  { id: 'python', label: 'Python 3' },
  { id: 'cpp', label: 'C++' },
];

export function LanguageSwitch() {
  const language = useLeetCode((s) => s.language);
  const { switchLanguage } = useLeetCodeActions();
  return (
    <div role="radiogroup" aria-label="Solution language" className="flex h-9 gap-1 rounded-xl p-1" style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}>
      {OPTIONS.map((o) => (
        <button
          key={o.id}
          role="radio"
          aria-checked={language === o.id}
          onClick={() => switchLanguage(o.id)}
          className="focus-ring rounded-lg px-3 text-xs font-medium transition-colors"
          style={language === o.id ? { background: 'var(--glass-bg-active)', color: 'var(--text)' } : { color: 'var(--text-muted)' }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
