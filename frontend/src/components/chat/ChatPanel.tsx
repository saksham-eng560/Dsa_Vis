/** "Ask CodeLens" — a tutor chat that knows your code, problem and current dry-run step. */
import { AnimatePresence, motion } from 'framer-motion';
import { Eraser, MessageCircleQuestion, X } from 'lucide-react';
import { useEffect, useRef } from 'react';

import { useChat } from '../../stores/chatStore';
import { GlowButton } from '../ui/GlowButton';
import { ChatComposer } from './ChatComposer';
import { ChatThread } from './ChatThread';


export function ChatPanel() {
  const { open, messages, setOpen, clear } = useChat();
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

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

            <ChatThread />
            <div className="border-t p-3" style={{ borderColor: 'var(--glass-border)' }}>
              <ChatComposer ref={inputRef} onEscape={() => setOpen(false)} />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
