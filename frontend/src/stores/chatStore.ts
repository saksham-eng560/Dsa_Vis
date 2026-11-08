/** Chat with the CodeLens tutor: messages, open state and streaming status. */
import { create } from 'zustand';

import type { ChatTurn } from '../services/api';

interface ChatState {
  open: boolean;
  messages: ChatTurn[];
  streaming: boolean;
  error: string | null;
  setOpen: (open: boolean) => void;
  push: (turn: ChatTurn) => void;
  appendToLast: (text: string) => void;
  setStreaming: (streaming: boolean, error?: string | null) => void;
  clear: () => void;
}

export const useChat = create<ChatState>((set) => ({
  open: false,
  messages: [],
  streaming: false,
  error: null,
  setOpen: (open) => set({ open }),
  push: (turn) => set((s) => ({ messages: [...s.messages, turn] })),
  appendToLast: (text) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last) msgs[msgs.length - 1] = { ...last, content: last.content + text };
      return { messages: msgs };
    }),
  setStreaming: (streaming, error = null) => set({ streaming, error }),
  clear: () => set({ messages: [], error: null }),
}));
