/** Frosted global navigation bar: wordmark, section links, model status, history, theme. */
import { History, Moon, Sun } from 'lucide-react';

import { useHealth } from '../../hooks/useHealth';
import { useTheme } from '../../hooks/useTheme';
import { useAppStore } from '../../stores/appStore';

function StatusPill() {
  const health = useHealth();
  const { color, text, title } =
    health.kind === 'loading'
      ? { color: 'var(--text-faint)', text: 'Connecting', title: '' }
      : health.kind === 'offline'
        ? { color: 'var(--accent-danger)', text: 'Backend offline', title: 'Start the API: ./start.sh' }
        : health.health.llm_available
          ? { color: 'var(--accent-secondary)', text: health.health.llm_model ?? 'AI ready', title: `AI via ${health.health.llm_provider}` }
          : { color: 'var(--accent-warning)', text: 'Offline mode', title: 'No AI model — tracing, flowcharts and Big-O still work.' };
  return (
    <span className="hidden items-center gap-2 text-xs sm:flex" style={{ color: 'var(--text-muted)' }} title={title} role="status">
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      <span className="max-w-[11rem] truncate">{text}</span>
    </span>
  );
}

const ghost = 'focus-ring flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-[var(--surface-3)]';

export function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const setSidebar = useAppStore((s) => s.setSidebar);
  return (
    <header
      className="sticky top-0 z-30 border-b"
      style={{ background: 'var(--nav-bg)', borderColor: 'var(--separator)', backdropFilter: 'saturate(180%) blur(20px)', WebkitBackdropFilter: 'saturate(180%) blur(20px)' }}
    >
      <nav className="mx-auto flex h-[52px] max-w-[1600px] items-center gap-6 px-5" aria-label="Main">
        <a href="#overview" className="focus-ring flex items-center gap-2 rounded-lg" aria-label="CodeLens overview">
          <img src="/favicon.svg" alt="" className="h-6 w-6" />
          <span className="text-[15px] font-semibold tracking-tight">CodeLens</span>
        </a>
        <div className="hidden items-center gap-6 text-[13px] md:flex" style={{ color: 'var(--text-muted)' }}>
          <a href="#overview" className="transition-colors hover:text-[var(--text)]">Overview</a>
          <a href="#workspace" className="transition-colors hover:text-[var(--text)]">Workspace</a>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <StatusPill />
          <button className={ghost} aria-label="Open history" title="History" onClick={() => setSidebar(true)}>
            <History size={16} />
          </button>
          <button className={ghost} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} title="Appearance" onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </nav>
    </header>
  );
}
