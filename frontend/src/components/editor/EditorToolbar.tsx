/** Editor actions: language, presets, upload, share, clear, analyze. */
import { Eraser, FileUp, FlaskConical, Link2, Sparkles } from 'lucide-react';
import { useRef } from 'react';

import { useLeetCodeActions } from '../../hooks/useLeetCodeActions';
import { useAppStore } from '../../stores/appStore';
import { useLeetCode } from '../../stores/leetcodeStore';
import { LanguageSwitch } from '../leetcode/LanguageSwitch';
import type { Language } from '../../types';
import { PRESETS } from '../../utils/presets';
import { GlowButton } from '../ui/GlowButton';
import { LanguageSelector } from './LanguageSelector';

interface EditorToolbarProps {
  detected: Language;
  onAnalyze: () => void;
  onShare: () => void;
  onFile: (file: File) => void;
}

export function EditorToolbar({ detected, onAnalyze, onShare, onFile }: EditorToolbarProps) {
  const language = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const busy = useAppStore((s) => s.status === 'analyzing');
  const fileInput = useRef<HTMLInputElement>(null);
  const lcMode = useLeetCode((s) => s.mode === 'leetcode');
  const hasProblem = useLeetCode((s) => s.problem !== null);
  const running = useLeetCode((s) => s.running);
  const { runAll } = useLeetCodeActions();

  const loadPreset = (id: string) => {
    const preset = PRESETS.find((p) => p.id === id);
    if (!preset) return;
    const { setCode, setLanguage: setLang, setEntryCall } = useAppStore.getState();
    setCode(preset.code);
    setLang(preset.language);
    setEntryCall(preset.entryCall ?? '');
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {lcMode ? (
        <LanguageSwitch />
      ) : (
        <LanguageSelector value={language} detected={detected} onChange={setLanguage} />
      )}
      {!lcMode && (
      <select
        className="field max-w-[9.5rem] cursor-pointer"
        aria-label="Load an example"
        value=""
        onChange={(e) => loadPreset(e.target.value)}
      >
        <option value="" disabled>
          Examples…
        </option>
        {PRESETS.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title}
          </option>
        ))}
      </select>
      )}
      <input
        ref={fileInput}
        type="file"
        className="hidden"
        accept=".py,.js,.mjs,.ts,.tsx,.jsx,.cpp,.cc,.c,.h,.hpp,.java,.go,.rs,.txt"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = '';
        }}
      />
      <GlowButton iconOnly aria-label="Upload a file" title="Upload a file" icon={<FileUp size={16} />} onClick={() => fileInput.current?.click()} />
      <GlowButton iconOnly aria-label="Copy share link" title="Copy share link" icon={<Link2 size={16} />} onClick={onShare} />
      <GlowButton
        iconOnly
        aria-label="Clear editor"
        title="Clear editor"
        icon={<Eraser size={16} />}
        onClick={() => useAppStore.getState().setCode('')}
      />
      {lcMode && (
        <GlowButton
          className="ml-auto"
          icon={<FlaskConical size={16} />}
          onClick={() => void runAll()}
          disabled={!hasProblem || running}
          title="Run your solution on every test case"
        >
          {running ? 'Running…' : 'Run tests'}
        </GlowButton>
      )}
      <GlowButton
        variant="glow"
        className={lcMode ? '' : 'ml-auto'}
        icon={<Sparkles size={16} />}
        onClick={onAnalyze}
        disabled={busy}
        aria-keyshortcuts="Control+Enter"
        title="Analyze (Ctrl/⌘ + Enter)"
      >
        {busy ? 'Analyzing…' : lcMode ? 'Visualize' : 'Analyze'}
      </GlowButton>
    </div>
  );
}
