/** Top navigation: logo, model status, history toggle, theme toggle. */
import { History, Moon, Sun } from 'lucide-react';

import { useHealth } from '../../hooks/useHealth';
import { useTheme } from '../../hooks/useTheme';
import { useAppStore } from '../../stores/appStore';
import { GlowButton } from '../ui/GlowButton';

function StatusPill() {
  const health = useHealth();
  const { color, text, title } =
    health.kind === 'loading'
      ? { color: 'var(--text-faint)', text: 'Connecting…', title: '' }
      : health.kind === 'offline'
        ? { color: 'var(--accent-danger)', text: 'Backend offline', title: 'Start the FastAPI server on port 8000' }
        : health.health.llm_available
          ? { color: 'var(--accent-secondary)', text: health.health.llm_model ?? 'AI ready', title: `LLM via ${health.health.llm_provider}` }
          : { color: 'var(--accent-warning)', text: 'Static mode', title: 'No LLM reachable — tracing, flowcharts and Big-O still work. Start Ollama for AI explanations.' };
  return (
    <span className="chip hidden sm:inline-flex" title={title} role="status">
      <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      <span className="max-w-[12rem] truncate">{text}</span>
    </span>
  );
}

export function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const setSidebar = useAppStore((s) => s.setSidebar);
  return (
    <header className="glass relative z-20 mx-3 mt-3 flex items-center gap-3 px-4 py-2.5 md:mx-5">
      <a href="/" className="focus-ring flex items-center gap-2.5 rounded-lg" aria-label="CodeLens home">
        <img src="/favicon.svg" alt="" className="h-8 w-8" />
        <span className="text-lg font-bold tracking-tight">
          Code<span className="bg-gradient-to-r from-indigo-300 to-emerald-300 bg-clip-text text-transparent">Lens</span>
        </span>
      </a>
      <span className="hidden text-xs md:inline" style={{ color: 'var(--text-faint)' }}>AI code visualiser & DSA analyser</span>
      <div className="ml-auto flex items-center gap-2">
        <StatusPill />
        <GlowButton iconOnly aria-label="Open history" title="History" icon={<History size={16} />} onClick={() => setSidebar(true)} />
        <GlowButton
          iconOnly
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title="Toggle theme"
          icon={theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          onClick={toggleTheme}
        />
      </div>
    </header>
  );
}
