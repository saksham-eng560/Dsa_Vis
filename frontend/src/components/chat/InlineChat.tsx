/** Chat box embedded at the bottom of the Explain tab (same conversation as the floating panel). */
import { Eraser, MessageCircleQuestion } from 'lucide-react';

import { useChat } from '../../stores/chatStore';
import { ChatComposer } from './ChatComposer';
import { ChatThread } from './ChatThread';

export function InlineChat() {
  const hasMessages = useChat((s) => s.messages.length > 0);
  const clear = useChat((s) => s.clear);
  return (
    <section className="glass-inset flex flex-col gap-3 p-4" aria-label="Ask about this code">
      <header className="flex items-center gap-2">
        <MessageCircleQuestion size={16} aria-hidden style={{ color: 'var(--accent-primary)' }} />
        <h3 className="text-sm font-semibold">Still have a doubt? Ask about this code</h3>
        <span className="hidden text-xs sm:inline" style={{ color: 'var(--text-faint)' }}>
          — the tutor sees your code, the problem and the current dry-run step
        </span>
        {hasMessages && (
          <button className="chip focus-ring ml-auto cursor-pointer" onClick={clear} aria-label="Clear chat">
            <Eraser size={12} aria-hidden /> Clear
          </button>
        )}
      </header>
      <ChatThread compact />
      <ChatComposer />
    </section>
  );
}
