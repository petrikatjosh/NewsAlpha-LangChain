import { useState, useRef, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

interface Message {
  role: "user" | "bot";
  text: string;
}

const SUGGESTIONS = [
  "Which sector is most accurate?",
  "Tell me about XLK",
  "Which news source is best?",
  "Cross-sector correlations",
  "Next-day accuracy",
  "How much data?",
];

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "bot",
      text: "Hi! I'm the NewsAlpha assistant. Ask me about sector accuracy, news sources, correlations, or any of our findings.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = { role: "user", text: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text.trim() }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "bot", text: data.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Couldn't reach the API. Is the Flask server running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  // ── Toggle button (always visible) ──
  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={styles.fab}>
        <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </button>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.dot} />
          <span style={styles.headerTitle}>NewsAlpha Assistant</span>
        </div>
        <button onClick={() => setOpen(false)} style={styles.closeBtn}>
          ✕
        </button>
      </div>

      {/* Messages */}
      <div style={styles.messagesArea}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              ...styles.messageBubble,
              ...(msg.role === "user" ? styles.userBubble : styles.botBubble),
            }}
          >
            <pre style={styles.messageText}>{msg.text}</pre>
          </div>
        ))}
        {loading && (
          <div style={{ ...styles.messageBubble, ...styles.botBubble }}>
            <span style={styles.loadingDots}>●  ●  ●</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions (only show when few messages) */}
      {messages.length <= 2 && (
        <div style={styles.suggestions}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              style={styles.suggestionBtn}
              onClick={() => sendMessage(s)}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={styles.inputArea}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about our findings..."
          style={styles.input}
          disabled={loading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          style={{
            ...styles.sendBtn,
            opacity: loading || !input.trim() ? 0.4 : 1,
          }}
        >
          ↑
        </button>
      </div>
    </div>
  );
}

/* ── Styles matching NewsAlpha dark theme ── */
const styles: Record<string, React.CSSProperties> = {
  fab: {
    position: "fixed",
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #22c55e, #16a34a)",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 20px rgba(34,197,94,0.4)",
    zIndex: 9999,
    transition: "transform 0.2s",
  },
  container: {
    position: "fixed",
    bottom: 24,
    right: 24,
    width: 400,
    maxWidth: "calc(100vw - 48px)",
    height: 520,
    maxHeight: "calc(100vh - 48px)",
    background: "#0f1729",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    boxShadow: "0 8px 40px rgba(0,0,0,0.5)",
    zIndex: 9999,
    fontFamily: "'DM Sans', sans-serif",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 16px",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
    background: "#111b30",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#22c55e",
  },
  headerTitle: {
    color: "#e2e8f0",
    fontSize: 14,
    fontWeight: 600,
    letterSpacing: "0.02em",
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "#64748b",
    cursor: "pointer",
    fontSize: 16,
    padding: "4px 8px",
  },
  messagesArea: {
    flex: 1,
    overflowY: "auto",
    padding: "16px 12px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  messageBubble: {
    maxWidth: "85%",
    padding: "10px 14px",
    borderRadius: 12,
    fontSize: 13,
    lineHeight: 1.5,
  },
  userBubble: {
    alignSelf: "flex-end",
    background: "linear-gradient(135deg, #22c55e, #16a34a)",
    color: "#fff",
    borderBottomRightRadius: 4,
  },
  botBubble: {
    alignSelf: "flex-start",
    background: "#1a2540",
    color: "#cbd5e1",
    borderBottomLeftRadius: 4,
    border: "1px solid rgba(255,255,255,0.04)",
  },
  messageText: {
    margin: 0,
    whiteSpace: "pre-wrap",
    fontFamily: "'DM Sans', sans-serif",
    fontSize: 13,
    lineHeight: 1.5,
  },
  loadingDots: {
    color: "#64748b",
    fontSize: 14,
    animation: "pulse 1.2s infinite",
  },
  suggestions: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
    padding: "0 12px 12px",
  },
  suggestionBtn: {
    background: "#1a2540",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 20,
    color: "#94a3b8",
    fontSize: 11,
    padding: "5px 12px",
    cursor: "pointer",
    transition: "all 0.15s",
    fontFamily: "'DM Sans', sans-serif",
  },
  inputArea: {
    display: "flex",
    gap: 8,
    padding: "12px",
    borderTop: "1px solid rgba(255,255,255,0.06)",
    background: "#111b30",
  },
  input: {
    flex: 1,
    background: "#0f1729",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 10,
    color: "#e2e8f0",
    padding: "10px 14px",
    fontSize: 13,
    outline: "none",
    fontFamily: "'DM Sans', sans-serif",
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 10,
    background: "linear-gradient(135deg, #22c55e, #16a34a)",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    fontSize: 18,
    fontWeight: 700,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "opacity 0.15s",
  },
};
