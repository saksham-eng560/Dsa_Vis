/** "Ask CodeLens" — a tutor chat that knows your code, problem and current dry-run step. */
import { AnimatePresence, motion } from 'framer-motion';
import { Eraser, MessageCircleQuestion, Send, Square, X } from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';

import { useChatActions } from '../../hooks/useChat';
import { useAppStore } from '../../stores/appStore';
import { useChat } from '../../stores/chatStore';
import { GlowButton } from '../ui/GlowButton';
import { Markdown } from './Markdown';

const SUGGESTIONS = [
  'Explain the current dry-run step',
  'Why is my solution this time complexity?',
  'Which edge cases could break my code?',
  'Give me a hint to optimise this',
  'Why is my test failing?',
];

export function ChatPanel() {
  const { open, messages, streaming, setOpen, clear } = useChat();
  const { send, stop } = useChatActions();
  const hasCode = useAppStore((s) => s.code.trim().length > 0);
  const [draft, setDraft] = useState('');
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const submit = (text = draft) => {
    if (!text.trim()) return;
    void send(text);
    setDraft('');
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    } else if (e.key === 'Escape') setOpen(false);
  };

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            onClick={() => setOpen(true)}
            className="btn btn-glow focus-ring fixed bottom-5 left-5 z-40 !h-12 !rounded-full !px-5 shadow-2xl"
            aria-label="Ask CodeLens a question"
          >
            <MessageCircleQuestion size={18} /> Ask CodeLens
          </motion.button>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {open && (
          <motion.aside
            role="dialog"
            aria-label="Ask CodeLens"
            initial={{ x: '110%' }}
            animate={{ x: 0 }}
            exit={{ x: '110%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 32 }}
            className="fixed inset-y-3 right-3 z-40 flex w-[min(26rem,calc(100vw-1.5rem))] flex-col rounded-2xl shadow-2xl"
            style={{ background: 'var(--surface-solid)', border: '1px solid var(--glass-border-hover)' }}
          >
            <header className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: 'var(--glass-border)' }}>
              <MessageCircleQuestion size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden />
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold">Ask CodeLens</h2>
                <p className="truncate text-[0.7rem]" style={{ color: 'var(--text-faint)' }}>
                  Knows your code, the problem and the current dry-run step
                </p>
              </div>
              {messages.length > 0 && <GlowButton iconOnly aria-label="Clear chat" icon={<Eraser size={15} />} onClick={clear} />}
              <GlowButton iconOnly aria-label="Close chat" icon={<X size={16} />} onClick={() => setOpen(false)} />
            </header>

            <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4 scroll-thin" aria-live="polite">
              {messages.length === 0 && (
                <div className="space-y-3">
                  <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    {hasCode ? 'Ask anything about your code — doubts, hints, why a test fails…' : 'Paste or write some code first, then ask away.'}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map((s) => (
                      <button key={s} className="chip focus-ring cursor-pointer text-left !py-1.5" onClick={() => submit(s)} disabled={streaming}>
                        {s}
                      </button>
                    ))}
                  </div>
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

            <div className="border-t p-3" style={{ borderColor: 'var(--glass-border)' }}>
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  className="field h-auto max-h-32 min-h-[2.5rem] flex-1 resize-none py-2 leading-5"
                  rows={2}
                  placeholder="Ask a doubt… (Enter to send, Shift+Enter for a new line)"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={onKey}
                  aria-label="Your question"
                />
                {streaming ? (
                  <GlowButton iconOnly aria-label="Stop" icon={<Square size={14} />} onClick={stop} />
                ) : (
                  <GlowButton variant="glow" iconOnly aria-label="Send" icon={<Send size={15} />} onClick={() => submit()} disabled={!draft.trim()} />
                )}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
