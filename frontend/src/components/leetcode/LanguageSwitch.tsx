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
    <div role="radiogroup" aria-label="Solution language" className="flex h-9 gap-0.5 rounded-[12px] p-[3px]" style={{ background: 'var(--surface-3)' }}>
      {OPTIONS.map((o) => (
        <button
          key={o.id}
          role="radio"
          aria-checked={language === o.id}
          onClick={() => switchLanguage(o.id)}
          className="focus-ring rounded-[9px] px-3 text-xs font-medium transition-all"
          style={language === o.id ? { background: 'var(--surface-solid)', color: 'var(--text)', boxShadow: '0 3px 8px rgba(0,0,0,0.12)' } : { color: 'var(--text-muted)' }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
