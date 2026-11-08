/** Question box: Enter sends, Shift+Enter adds a line, Stop cancels a streaming answer. */
import { Send, Square } from 'lucide-react';
import { forwardRef, useState, type KeyboardEvent } from 'react';

import { useChatActions } from '../../hooks/useChat';
import { useChat } from '../../stores/chatStore';
import { GlowButton } from '../ui/GlowButton';

export const ChatComposer = forwardRef<HTMLTextAreaElement, { onEscape?: () => void }>(function ChatComposer(
  { onEscape },
  ref,
) {
  const streaming = useChat((s) => s.streaming);
  const { send, stop } = useChatActions();
  const [draft, setDraft] = useState('');

  const submit = () => {
    if (!draft.trim()) return;
    void send(draft);
    setDraft('');
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    } else if (e.key === 'Escape') onEscape?.();
  };

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={ref}
        className="field h-auto max-h-32 min-h-[2.75rem] flex-1 resize-none py-2.5 leading-5"
        rows={2}
        placeholder="Ask your own doubt about this code… (Enter to send, Shift+Enter for a new line)"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKey}
        aria-label="Your question"
      />
      {streaming ? (
        <GlowButton aria-label="Stop" icon={<Square size={14} />} onClick={stop}>
          Stop
        </GlowButton>
      ) : (
        <GlowButton variant="glow" aria-label="Send" icon={<Send size={15} />} onClick={submit} disabled={!draft.trim()}>
          Ask
        </GlowButton>
      )}
    </div>
  );
});
