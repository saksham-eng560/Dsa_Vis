/** Small footer with keyboard hints. */
export function Footer() {
  return (
    <footer className="relative z-10 px-5 pb-4 pt-1 text-center text-[0.7rem]" style={{ color: 'var(--text-faint)' }}>
      <kbd className="chip !py-0 font-mono">Ctrl/⌘ + Enter</kbd> analyse · <kbd className="chip !py-0 font-mono">← →</kbd> step ·{' '}
      <kbd className="chip !py-0 font-mono">Space</kbd> play · Code runs in a sandbox and is never stored on the server.
    </footer>
  );
}
