import { useState, useRef, useEffect, useId, useCallback } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/ask/";
const REQUEST_TIMEOUT_MS = 12_000;

const CATEGORY_META = {
  schedules: { labelHe: "לוח בחינות",  labelEn: "Schedules",  icon: "📅" },
  general:   { labelHe: "מידע כללי",   labelEn: "General",    icon: "🏛️" },
  technical: { labelHe: "תמיכה טכנית", labelEn: "Technical",  icon: "⚙️" },
  unknown:   { labelHe: "כללי",        labelEn: "General",    icon: "💬" },
};

function isHebrew(text = "") {
  const heChars = (text.match(/[֐-׿]/g) || []).length;
  return heChars / Math.max(text.length, 1) > 0.25;
}

// ─────────────────────────────────────────────────────────────────────────────
// ChatBubble
// ─────────────────────────────────────────────────────────────────────────────

function ChatBubble({ message, isLatest }) {
  const { role, text, category, isError } = message;
  const isUser = role === "user";
  const hebrew = isHebrew(text);
  const dir    = hebrew ? "rtl" : "ltr";
  const meta   = CATEGORY_META[category] || CATEGORY_META.unknown;

  return (
    <div
      className={[
        "bubble-row",
        isUser ? "bubble-row--user" : "bubble-row--ai",
        isLatest ? "bubble-row--latest" : "",
      ].filter(Boolean).join(" ")}
    >
      {!isUser && (
        <div className="avatar avatar--ai" aria-hidden="true">
          <span className="avatar__glyph">✦</span>
        </div>
      )}

      <div className="bubble-col">
        {!isUser && (
          <span className="bubble-sender" aria-hidden="true">
            עוזר הקמפוס
          </span>
        )}

        <div
          className={[
            "bubble",
            isUser  ? "bubble--user" : "bubble--ai",
            isError ? "bubble--error" : "",
          ].filter(Boolean).join(" ")}
          lang={hebrew ? "he" : "en"}
          dir={dir}
          role={isError ? "alert" : undefined}
        >
          <p className="bubble__text">{text}</p>
        </div>

        {!isUser && category && !isError && (
          <div className="bubble__meta" dir="ltr">
            <span className="cat-tag" aria-label={`Category: ${meta.labelEn}`}>
              <span aria-hidden="true">{meta.icon}</span>
              <span>{hebrew ? meta.labelHe : meta.labelEn}</span>
            </span>
          </div>
        )}
      </div>

      {isUser && (
        <div className="avatar avatar--user" aria-hidden="true">
          <span className="avatar__glyph">את/ה</span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TypingIndicator
// ─────────────────────────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="bubble-row bubble-row--ai" aria-hidden="true">
      <div className="avatar avatar--ai">
        <span className="avatar__glyph">✦</span>
      </div>
      <div className="bubble bubble--ai bubble--typing">
        <span className="dot" style={{ "--i": 0 }} />
        <span className="dot" style={{ "--i": 1 }} />
        <span className="dot" style={{ "--i": 2 }} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// EmptyState — columnar prompt buttons, all uniform
// ─────────────────────────────────────────────────────────────────────────────

const PROMPTS = [
  { text: "מתי מועד א׳ של מבחן CS101?",             lang: "he", dir: "rtl", icon: "📅" },
  { text: "Where is room 204 in Engineering?",        lang: "en", dir: "ltr", icon: "🗺️" },
  { text: "מה שעות הקבלה של המזכירות?",              lang: "he", dir: "rtl", icon: "🕐" },
  { text: "I forgot my student portal password",      lang: "en", dir: "ltr", icon: "💻" },
  { text: "איפה הספרייה המרכזית?",                   lang: "he", dir: "rtl", icon: "📚" },
];

function EmptyState({ onPromptClick }) {
  return (
    <div className="empty" role="region" aria-label="Getting started">
      <div className="empty__hero" aria-hidden="true">
        <div className="empty__emblem">✦</div>
      </div>

      <div className="empty__text">
        <h2 className="empty__title" lang="he" dir="rtl">
          שלום! במה אוכל לעזור?
        </h2>
        <p className="empty__desc" lang="en">
          Ask about exam schedules, room locations, office hours, or tech support.
        </p>
      </div>

      <div className="empty__divider" aria-hidden="true" />

      <p className="empty__label">Suggested questions</p>

      <ul className="prompt-list" aria-label="Suggested questions — click to ask">
        {PROMPTS.map((p, i) => (
          <li key={i} style={{ "--delay": `${i * 55}ms` }}>
            <button
              type="button"
              className="prompt-btn"
              onClick={() => onPromptClick(p.text)}
              lang={p.lang}
              dir={p.dir}
            >
              <span className="prompt-btn__icon" aria-hidden="true">{p.icon}</span>
              <span className="prompt-btn__text">{p.text}</span>
              <span className="prompt-btn__arrow" aria-hidden="true">→</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────────────

export default function App() {
  const [messages,  setMessages]  = useState([]);
  const [inputText, setInputText] = useState("");
  const [loading,   setLoading]   = useState(false);

  const chatEndRef    = useRef(null);
  const inputRef      = useRef(null);
  const controllerRef = useRef(null);
  const sessionIdRef  = useRef(null);

  const inputId = useId();
  const liveId  = useId();

  // Initialize session ID on first mount
  useEffect(() => {
    if (!sessionIdRef.current) {
      sessionIdRef.current = crypto.randomUUID();
    }
  }, []);

  // Reset the entire conversation back to the empty/home state
  const resetChat = useCallback(() => {
    // Abort any in-flight request first
    controllerRef.current?.abort();
    setMessages([]);
    setInputText("");
    setLoading(false);
    // Generate a new session ID for the fresh conversation
    sessionIdRef.current = crypto.randomUUID();
    // Return focus to the input so keyboard users land somewhere sensible
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, loading]);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const sendMessage = useCallback(async (questionOverride) => {
    const question = (questionOverride ?? inputText).trim();
    if (!question || loading) return;

    setMessages(prev => [...prev, { id: Date.now(), role: "user", text: question }]);
    setInputText("");
    setLoading(true);

    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(API_URL, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ question, session_id: sessionIdRef.current }),
        signal:  controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        let detail = `Server error (HTTP ${response.status})`;
        if (response.status === 400) {
          const b = await response.json().catch(() => ({}));
          detail = b?.detail || "Invalid request. Please rephrase your question.";
        } else if (response.status === 429) {
          const b = await response.json().catch(() => ({}));
          detail = b?.retry_after_seconds
            ? `Too many requests. Please wait ${b.retry_after_seconds}s and try again.`
            : "Too many requests. Please wait a moment.";
        } else if (response.status >= 500) {
          detail = "Server error. Please try again shortly.";
        }
        setMessages(prev => [...prev, {
          id: Date.now(), role: "assistant",
          text: detail, isError: true, category: "unknown",
        }]);
        return;
      }

      const data = await response.json();
      setMessages(prev => [...prev, {
        id: Date.now(), role: "assistant",
        text: data.answer, category: data.category, isError: false,
      }]);

    } catch (err) {
      clearTimeout(timeoutId);
      const msg = err.name === "AbortError"
        ? "The request timed out. Check your connection and try again."
        : "Cannot reach the server. Ensure the backend is running on port 8000.";
      setMessages(prev => [...prev, {
        id: Date.now(), role: "assistant",
        text: msg, isError: true, category: "unknown",
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [inputText, loading]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }, [sendMessage]);

  const canSend     = !loading && inputText.trim().length > 0;
  const inputHebrew = isHebrew(inputText);

  return (
    <div className="app">
      {/* Skip-to-content (WCAG 2.4.1) */}
      <a href={`#${inputId}`} className="skip-link">
        Skip to message input
      </a>

      <div className="shell">

        {/* ── Header ── */}
        <header className="shell__header" role="banner">
          <div className="header-inner">
            <div className="header-brand" aria-label="Campus Assistant">
              <div className="header-emblem" aria-hidden="true">✦</div>
              <div className="header-titles">
                <span className="header-title-he" lang="he" dir="rtl">עוזר הקמפוס</span>
                <span className="header-title-en" lang="en">Campus Assistant</span>
              </div>
            </div>

            <div className="header-actions">
              {/* New Chat button — only shown when there are messages */}
              {messages.length > 0 && (
                <button
                  type="button"
                  className="new-chat-btn"
                  onClick={resetChat}
                  aria-label="Start a new chat — clear conversation history"
                  title="New Chat"
                >
                  <svg
                    className="new-chat-btn__icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-hidden="true"
                  >
                    {/* Compose / new-page icon */}
                    <path
                      d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="new-chat-btn__label">New Chat</span>
                </button>
              )}

              <div
                className="header-status"
                aria-live="polite"
                aria-atomic="true"
                role="status"
              >
              {loading ? (
                <span className="status-pill status-pill--busy">
                  <span className="status-pill__ring" aria-hidden="true" />
                  מעבד…
                </span>
              ) : (
                <span className="status-pill status-pill--idle">
                  <span className="status-pill__dot" aria-hidden="true" />
                  מוכן
                </span>
              )}
              </div>
            </div>
          </div>
          {/* Signature orange accent bar */}
          <div className="header-accent" aria-hidden="true" />
        </header>

        {/* ── Chat log ── */}
        <main className="shell__body" id="main-content" tabIndex={-1}>
          <div
            className="message-log"
            role="log"
            aria-label="Conversation history"
            aria-live="polite"
            aria-relevant="additions"
            aria-atomic="false"
            id={liveId}
          >
            {messages.length === 0 && !loading && (
              <EmptyState onPromptClick={(t) => sendMessage(t)} />
            )}

            {messages.map((msg, i) => (
              <ChatBubble
                key={msg.id}
                message={msg}
                isLatest={i === messages.length - 1}
              />
            ))}

            {loading && <TypingIndicator />}
            <div ref={chatEndRef} aria-hidden="true" />
          </div>
        </main>

        {/* ── Compose area ── */}
        <footer className="shell__footer">
          <form
            className="compose"
            onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
            aria-label="Send a question"
            noValidate
          >
            <label htmlFor={inputId} className="compose__label">
              <span lang="he" dir="rtl">שאל/י שאלה</span>
              <span aria-hidden="true"> · </span>
              <span lang="en">Ask a question</span>
            </label>

            <div className="compose__row">
              <div className="compose__field-wrap">
                <textarea
                  id={inputId}
                  ref={inputRef}
                  className="compose__field"
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="הקלד/י שאלה... · Type your question..."
                  rows={2}
                  maxLength={500}
                  disabled={loading}
                  aria-disabled={loading}
                  aria-describedby="compose-hint"
                  dir={inputHebrew ? "rtl" : "ltr"}
                  autoComplete="off"
                  spellCheck={false}
                />
              </div>

              <button
                type="submit"
                className={`send-btn ${canSend ? "send-btn--on" : ""}`}
                disabled={!canSend}
                aria-label={loading ? "Sending…" : "Send message"}
                aria-busy={loading}
              >
                {loading ? (
                  <span className="send-btn__spinner" aria-hidden="true" />
                ) : (
                  <svg className="send-btn__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </button>
            </div>

            <div className="compose__footer">
              <span id="compose-hint" className="compose__hint">
                Enter to send · Shift+Enter for new line
              </span>
              <span
                className={`compose__counter ${inputText.length >= 450 ? "compose__counter--warn" : ""}`}
                aria-live="polite"
                aria-label={`${inputText.length} of 500 characters`}
              >
                {inputText.length}/500
              </span>
            </div>
          </form>
        </footer>

      </div>
    </div>
  );
}
