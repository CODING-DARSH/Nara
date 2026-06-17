// NARA — Chat Page
import { useState, useEffect, useRef } from "react";
import { conversation } from "../services/api";

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div
      style={{
        display:       "flex",
        justifyContent:isUser ? "flex-end" : "flex-start",
        marginBottom:  "12px",
        animation:     "fadeUp 0.25s ease both",
      }}
    >
      <div
        style={{
          maxWidth:     "80%",
          padding:      "12px 16px",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          background:   isUser ? "var(--text-primary)" : "var(--surface)",
          color:        isUser ? "var(--bg)" : "var(--text-primary)",
          border:       isUser ? "none" : "1px solid var(--border)",
          fontSize:     "15px",
          lineHeight:   1.5,
          whiteSpace:   "pre-wrap",
        }}
      >
        {msg.content}

        {/* Inline recommendations */}
        {!isUser && msg.recommendations?.length > 0 && (
          <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
            {msg.recommendations.map((r, i) => (
              <div
                key={i}
                style={{
                  background:   "var(--surface-2)",
                  borderRadius: "10px",
                  padding:      "10px 12px",
                  border:       "1px solid var(--border)",
                }}
              >
                <div style={{ fontSize: "13px", fontWeight: 600, textTransform: "capitalize", marginBottom: "4px" }}>
                  {r.dish_name?.replace(/_/g, " ")}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  {r.health_compliant && (
                    <span style={{ fontSize: "11px", color: "var(--green)" }}>✓ healthy</span>
                  )}
                  {r.nutrition?.calories && (
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      {Math.round(r.nutrition.calories)} kcal
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Intent badge */}
        {!isUser && msg.intent && msg.intent !== "general_chat" && (
          <div style={{ marginTop: "8px" }}>
            <span
              style={{
                fontSize:   "10px",
                color:      "var(--text-tertiary)",
                fontStyle:  "italic",
              }}
            >
              {msg.intent.replace(/_/g, " ")} · {msg.intentMethod}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "12px" }}>
      <div
        style={{
          padding:      "14px 18px",
          borderRadius: "18px 18px 18px 4px",
          background:   "var(--surface)",
          border:       "1px solid var(--border)",
          display:      "flex",
          gap:          "5px",
          alignItems:   "center",
        }}
      >
        {[0, 1, 2].map(i => (
          <div
            key={i}
            style={{
              width:      "6px",
              height:     "6px",
              borderRadius:"50%",
              background: "var(--text-secondary)",
              animation:  `pulse 1.2s ease ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  "What should I eat for lunch?",
  "Had biryani for lunch",
  "How many calories in idli?",
  "Show my food graph",
  "Suggest something low GI",
  "Hungry near me 🍽",
];

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      id:      "welcome",
      role:    "assistant",
      content: "Hey! I'm NARA, your personal food intelligence assistant.\n\nTell me what you're craving, ask about nutrition, or just say what you ate — I'll handle the rest.",
    },
  ]);
  const [input,    setInput]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [sessionId]             = useState(() => Math.random().toString(36).slice(2));
  const bottomRef               = useRef(null);
  const inputRef                = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text) {
    const trimmed = (text || input).trim();
    if (!trimmed || loading) return;

    setInput("");
    setMessages(prev => [...prev, { id: Date.now(), role: "user", content: trimmed }]);
    setLoading(true);

    try {
      const res = await conversation.chat(trimmed, sessionId);
      setMessages(prev => [
        ...prev,
        {
          id:              Date.now() + 1,
          role:            "assistant",
          content:         res.message,
          intent:          res.intent,
          intentMethod:    res.intent_method,
          recommendations: res.recommendations || [],
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id:      Date.now() + 1,
          role:    "assistant",
          content: "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div
      style={{
        display:       "flex",
        flexDirection: "column",
        height:        "100dvh",
        paddingBottom: "var(--nav-height)",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding:        "56px 24px 16px",
          borderBottom:   "1px solid var(--border)",
          background:     "rgba(0,0,0,0.9)",
          backdropFilter: "blur(20px)",
          flexShrink:     0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width:        "36px",
              height:       "36px",
              borderRadius: "50%",
              background:   "var(--surface)",
              border:       "1px solid var(--border)",
              display:      "flex",
              alignItems:   "center",
              justifyContent:"center",
              fontSize:     "18px",
            }}
          >
            🤖
          </div>
          <div>
            <div style={{ fontSize: "16px", fontWeight: 700 }}>NARA</div>
            <div style={{ fontSize: "11px", color: "var(--green)", display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />
              Online
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          flex:       1,
          overflowY:  "auto",
          padding:    "20px 24px",
          display:    "flex",
          flexDirection:"column",
        }}
      >
        {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div style={{ padding: "0 24px 12px", display: "flex", gap: "8px", overflowX: "auto" }}>
          {SUGGESTIONS.map(s => (
            <button
              key={s}
              onClick={() => send(s)}
              style={{
                padding:      "8px 14px",
                borderRadius: "100px",
                background:   "var(--surface)",
                border:       "1px solid var(--border)",
                color:        "var(--text-secondary)",
                fontSize:     "12px",
                whiteSpace:   "nowrap",
                flexShrink:   0,
              }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div
        style={{
          padding:        "12px 16px",
          borderTop:      "1px solid var(--border)",
          background:     "rgba(0,0,0,0.9)",
          backdropFilter: "blur(20px)",
          display:        "flex",
          gap:            "10px",
          alignItems:     "flex-end",
          flexShrink:     0,
        }}
      >
        <div
          style={{
            flex:         1,
            background:   "var(--surface)",
            border:       "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding:      "10px 16px",
            display:      "flex",
            alignItems:   "flex-end",
          }}
        >
          <textarea
            ref={inputRef}
            style={{
              flex:      1,
              fontSize:  "15px",
              resize:    "none",
              maxHeight: "120px",
              lineHeight:1.5,
              overflowY: "auto",
            }}
            rows={1}
            placeholder="Message NARA..."
            value={input}
            onChange={e => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = e.target.scrollHeight + "px";
            }}
            onKeyDown={handleKey}
          />
        </div>
        <button
          onClick={() => send()}
          disabled={!input.trim() || loading}
          style={{
            width:        "44px",
            height:       "44px",
            borderRadius: "50%",
            background:   input.trim() && !loading ? "var(--text-primary)" : "var(--surface)",
            border:       "1px solid var(--border)",
            display:      "flex",
            alignItems:   "center",
            justifyContent:"center",
            flexShrink:   0,
            transition:   "all 0.2s",
          }}
        >
          {loading ? (
            <span className="spinner" style={{ width: "18px", height: "18px" }} />
          ) : (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path
                d="M16 9L2 2L5 9L2 16L16 9Z"
                fill={input.trim() ? "var(--bg)" : "var(--text-secondary)"}
              />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}