import React, { useState, useEffect, useRef } from 'react';
import '../assets/style.css';
import chatbotIconUrl from '../assets/chatbot-icon.svg';
import { Chatbot } from '../logic/chatbot.js';

const chatbotInstance = new Chatbot();

const STORAGE_KEYS = {
  sessionId: 'dhanada_session_id',
  history: 'dhanada_chat_history',
  state: 'dhanada_chat_state',
  widgetOpen: 'dhanada_widget_open',
};

const DEFAULT_SUGGESTIONS = [
  'What is SIP?',
  'Compare Horizon Bluechip and Cedar Balanced Advantage',
  'Show sample market news',
  'Suggest a fund for 5 years',
];

const WELCOME_MESSAGE = 'Hello. I am your Dhanada investment assistant.\nI can explain funds, SIP, risk, tax, KYC, NAV, and sample recommendations.';

export default function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(() => localStorage.getItem(STORAGE_KEYS.widgetOpen) === 'true');
  const [sessionId, setSessionId] = useState(() => {
    let id = localStorage.getItem(STORAGE_KEYS.sessionId);
    if (!id) {
      id = (typeof crypto !== 'undefined' && crypto.randomUUID) 
        ? crypto.randomUUID() 
        : 'sess-' + Math.random().toString(36).substring(2, 15);
      localStorage.setItem(STORAGE_KEYS.sessionId, id);
    }
    return id;
  });
  const [messages, setMessages] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.history);
      if (stored) return JSON.parse(stored);
    } catch (e) { }
    return [{ role: 'bot', text: WELCOME_MESSAGE }];
  });
  const [chatState, setChatState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.state);
      if (stored) return JSON.parse(stored);
    } catch (e) { }
    return {};
  });
  const [suggestions, setSuggestions] = useState(DEFAULT_SUGGESTIONS);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [healthStatus, setHealthStatus] = useState('Checking');
  const [healthOk, setHealthOk] = useState(false);

  const historyRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    console.log("ChatbotWidget Mounted");
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.widgetOpen, String(isOpen));
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current.focus(), 120);
    }
  }, [isOpen]);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, isTyping, suggestions]);

  useEffect(() => {
    // Local chatbot is always online
    setHealthOk(true);
    setHealthStatus('Online');
  }, []);

  const pushMessage = (role, text, quickReplies = []) => {
    setMessages((prev) => {
      const clearedPrev = prev.map(msg => ({ ...msg, quickReplies: [] }));
      const updated = [...clearedPrev, { role, text, quickReplies }];
      localStorage.setItem(STORAGE_KEYS.history, JSON.stringify(updated));
      return updated;
    });
  };

  const updateStateAndSuggestions = (newState, quickReplies) => {
    setChatState(newState);
    localStorage.setItem(STORAGE_KEYS.state, JSON.stringify(newState));
    setSuggestions(quickReplies || []);
  };

  const handleSend = async (text) => {
    if (!text.trim() || isBusy) return;

    setSuggestions([]);
    setIsOpen(true);
    setIsBusy(true);
    pushMessage('user', text);
    setInputText('');

    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    setIsTyping(true);

    try {
      const data = await chatbotInstance.processMessage(sessionId, text);
      pushMessage('bot', data.reply, data.quickReplies);
      updateStateAndSuggestions(data.state, data.quickReplies);
    } catch (error) {
      console.error(error);
      pushMessage('bot', 'Sorry, I am having trouble connecting right now. Please try again later.');
    } finally {
      setIsTyping(false);
      setIsBusy(false);
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 50);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    handleSend(inputText);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(inputText);
    }
  };

  const handleInput = (e) => {
    setInputText(e.target.value);
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
    }
  };

  const handleNewChat = () => {
    const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : 'sess-' + Math.random().toString(36).substring(2, 15);
    setSessionId(newId);
    localStorage.setItem(STORAGE_KEYS.sessionId, newId);

    const initialMsgs = [{ role: 'bot', text: WELCOME_MESSAGE }];
    setMessages(initialMsgs);
    localStorage.setItem(STORAGE_KEYS.history, JSON.stringify(initialMsgs));

    setChatState({});
    localStorage.removeItem(STORAGE_KEYS.state);

    setSuggestions(DEFAULT_SUGGESTIONS);
    setInputText('');
    setIsOpen(true);
  };

  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, [isOpen]);

  return (
    <>
      <button
        id="widgetLauncher"
        className={`widget-launcher ${isOpen ? 'is-open' : ''}`}
        type="button"
        aria-controls="chatWidget"
        aria-expanded={isOpen}
        aria-label="Open Dhanada chatbot"
        onClick={() => setIsOpen(true)}
      >
        <span className="widget-launcher-ring"></span>
        <img src={chatbotIconUrl} alt="" className="widget-launcher-icon" />
        <span className="widget-launcher-text">
          <strong>Dhanada Chat</strong>
          <small>Ask anything</small>
        </span>
      </button >

      <section id="chatWidget" className={`chat-widget ${isOpen ? 'is-open' : ''}`} aria-hidden={!isOpen}>
        <header className="chat-widget-header">
          <div className="widget-brand">
            <img src={chatbotIconUrl} alt="Dhanada bot icon" className="widget-brand-icon" />
            <div>
              <p className="widget-brand-kicker">Dhanada</p>
              <h2>Investment Assistant</h2>
            </div>
          </div>

          <div className="widget-header-actions">
            <div className="status-pill">
              <span className={`status-dot ${healthOk ? 'ok' : 'error'}`}></span>
              <span id="healthText">{healthStatus}</span>
            </div>
            <button id="newChatButton" className="icon-button" type="button" aria-label="Start new chat" onClick={handleNewChat}>↺</button>
            <button id="closeWidgetButton" className="icon-button" type="button" aria-label="Close chat" onClick={() => setIsOpen(false)}>✕</button>
          </div>
        </header >

        <div className="widget-intro">
          <p>Ask about SIP, funds, tax, NAV, risk, KYC, and recommendations.</p>
        </div>

        <div id="suggestionBar" className="suggestion-bar" aria-label="Quick prompts">
          {suggestions.map((s, idx) => (
            <button key={idx} type="button" className="suggestion-chip" onClick={() => handleSend(s)} disabled={isBusy}>
              {s}
            </button>
          ))}
        </div>

        <div id="chatHistory" className="chat-history" aria-live="polite" ref={historyRef}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-row ${msg.role}`}>
              <div className={`message ${msg.role}`}>
                {msg.role === 'bot' && (
                  <div className="message-meta">
                    <span className="message-avatar">D</span>
                    <span>Dhanada</span>
                  </div>
                )}
                <div>{msg.text}</div>
                {msg.quickReplies && msg.quickReplies.length > 0 && (
                  <div className="quick-replies-container">
                    {msg.quickReplies.map((qr, qrIdx) => (
                      <button 
                        key={qrIdx} 
                        type="button"
                        className="quick-reply-btn" 
                        onClick={() => handleSend(qr)}
                        disabled={isBusy}
                      >
                        {qr}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div >
          ))
          }
          {
            isTyping && (
              <div className="message-row bot">
                <div className="message bot">
                  <div className="message-meta">
                    <span className="message-avatar">D</span>
                    <span>Dhanada</span>
                  </div>
                  <div className="typing-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )
          }
        </div >

        <form id="composer" className="composer" onSubmit={handleFormSubmit}>
          <label className="sr-only" htmlFor="messageInput">Type your message</label>
          <textarea
            id="messageInput"
            ref={inputRef}
            rows="1"
            maxLength="1000"
            placeholder="Type your question..."
            value={inputText}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isBusy}
          ></textarea>
          <button id="sendButton" type="submit" disabled={!inputText.trim() || isBusy}>Send</button>
        </form>
      </section >
    </>
  );
}
