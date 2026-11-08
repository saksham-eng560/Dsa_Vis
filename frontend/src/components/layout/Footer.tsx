/** Quiet footer with keyboard shortcuts. */
export function Footer() {
  return (
    <footer className="mx-auto max-w-[1600px] border-t px-5 py-6 text-xs" style={{ color: 'var(--text-faint)', borderColor: 'var(--separator)' }}>
      <p>
        Shortcuts: <kbd className="font-mono">⌘/Ctrl + Enter</kbd> analyse · <kbd className="font-mono">← →</kbd> step ·{' '}
        <kbd className="font-mono">Space</kbd> play · drag the divider to resize the editor. Code runs in a local sandbox and never leaves your machine.
      </p>
    </footer>
  );
}
