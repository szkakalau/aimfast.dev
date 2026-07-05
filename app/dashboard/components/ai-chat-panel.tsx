'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';

type Message = {
  role: 'user' | 'assistant';
  content: string;
};

type Props = {
  t: Record<string, string>;
  cardType: 'decision' | 'competitor' | 'system';
  isOpen: boolean;
  onClose: () => void;
};

export function AiChatPanel({ t, cardType: _cardType, isOpen, onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      // Small delay for drawer animation
      const timer = setTimeout(() => inputRef.current?.focus(), 200);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');

    // MVP: placeholder response
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: t.aiChatPlaceholder || 'AI assistant is coming soon. I\'ll be able to answer questions about this card\'s data, suggest alternatives, and help you think through validation strategies.',
        },
      ]);
    }, 800);
  }, [input, t]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  if (!isOpen) return null;

  return (
    <div className="ai-chat-panel" role="dialog" aria-label={t.decisionAskAI || 'Ask AI'}>
      <div className="ai-chat-header">
        <span className="ai-chat-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
            <path d="M12 2a10 10 0 0 1 10 10h-4a6 6 0 0 0-6-6V2z" />
          </svg>
          {t.aiChatTitle || 'Ask AI'}
        </span>
        <button className="ai-chat-close" onClick={onClose} aria-label="Close">
          <X size={16} />
        </button>
      </div>

      <div className="ai-chat-messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="ai-chat-empty">
            <p>{t.aiChatWelcome || 'Ask me anything about this data — dig deeper into the evidence, explore alternatives, or validate assumptions.'}</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`ai-chat-msg ${msg.role}`}>
            <div className="ai-chat-msg-content">{msg.content}</div>
          </div>
        ))}
      </div>

      <div className="ai-chat-input-row">
        <input
          ref={inputRef}
          type="text"
          className="ai-chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t.aiChatPlaceholder || 'Ask a question…'}
        />
        <button className="ai-chat-send" onClick={handleSend} disabled={!input.trim()}>
          {t.aiChatSend || '→'}
        </button>
      </div>
    </div>
  );
}
