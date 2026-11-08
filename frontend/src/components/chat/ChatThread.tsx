/** Message list + suggested questions — shared by the inline chat and the floating panel. */
import { motion } from 'framer-motion';
import { useEffect, useRef } from 'react';

import { useChatActions } from '../../hooks/useChat';
import { useChat } from '../../stores/chatStore';
import { Markdown } from './Markdown';

const SUGGESTIONS = [
  'Explain the current dry-run step',
  'Why is this the time complexity?',
  'Which edge cases could break my code?',
  'Give me a hint to optimise this',
  'Why is my test failing?',
];

export function ChatThread({ compact = false }: { compact?: boolean }) {
  const messages = useChat((s) => s.messages);
  const streaming = useChat((s) => s.streaming);
  const { send } = useChatActions();
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  return (
    <div
      ref={listRef}
      className={`space-y-3 overflow-y-auto scroll-thin ${compact ? 'max-h-96' : 'flex-1 p-4'}`}
      aria-live="polite"
    >
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="chip focus-ring cursor-pointer text-left !py-1.5" onClick={() => void send(s)} disabled={streaming}>
              {s}
            </button>
          ))}
        </div>
      )}
      {messages.map((m, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 ${m.role === 'user' ? 'ml-auto' : ''}`}
          style={
            m.role === 'user'
              ? { background: 'color-mix(in srgb, var(--accent-primary) 28%, transparent)' }
              : { background: 'var(--glass-bg-hover)', border: '1px solid var(--glass-border)' }
          }
        >
          {m.role === 'assistant' ? (
            m.content ? <Markdown text={m.content} /> : <span className="caret text-sm" style={{ color: 'var(--text-faint)' }}>Thinking</span>
          ) : (
            <p className="whitespace-pre-wrap text-sm">{m.content}</p>
          )}
        </motion.div>
      ))}
    </div>
  );
}
