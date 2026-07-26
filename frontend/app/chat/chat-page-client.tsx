"use client";

/**
 * ChatPageClient — AI Copilot Interface
 *
 * Full-page chat interface that interacts with POST /api/v1/chat.
 * Features:
 * - Session tracking (client-generated UUID) to maintain context
 * - Realistic loading state (8-25s latency, no fake streaming)
 * - Distinct rendering for NO_EVIDENCE_RESPONSE
 * - Citations block below assistant messages
 */

import { useState, useRef, useEffect, useCallback } from "react";

// ─── Types (from backend schemas) ─────────────────────────────────────────────

interface CitationOut {
  document_id: string;
  document_name: string;
  section: string;
  page_number: number | null;
  asset_ids: string[];
  confidence: number;
  excerpt: string;
}

interface ChatResponseData {
  answer: string;
  citations: CitationOut[];
  confidence: number;
  followup_questions: string[];
  reasoning: string;
  related_assets: string[];
  diagnostics: Record<string, unknown>;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "error";
  text: string;
  citations?: CitationOut[];
  confidence?: number;
  isNoEvidence?: boolean;
}

const NO_EVIDENCE_TEXT = "I could not find supporting evidence in the available knowledge base.";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Sub-components ───────────────────────────────────────────────────────────

function CitationList({ citations }: { citations: CitationOut[] }) {
  const [expanded, setExpanded] = useState(false);
  if (!citations || citations.length === 0) return null;

  const displayList = expanded ? citations : citations.slice(0, 2);
  const hasMore = citations.length > 2;

  return (
    <div
      style={{
        marginTop: "12px",
        paddingTop: "12px",
        borderTop: "1px solid rgba(255, 255, 255, 0.1)",
      }}
    >
      <div
        style={{
          fontSize: "10px",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "#8A96A3",
          marginBottom: "8px",
          fontFamily: "'IBM Plex Sans', sans-serif",
        }}
      >
        Sources & Citations
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {displayList.map((cite, i) => (
          <div
            key={i}
            style={{
              padding: "6px 10px",
              backgroundColor: "rgba(0,0,0,0.2)",
              border: "1px solid rgba(255,255,255,0.05)",
              borderRadius: "2px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "4px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "#E8ECEF",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                }}
              >
                {cite.document_name || cite.document_id}
              </div>
              <div
                className="font-mono"
                style={{
                  fontSize: "10px",
                  color: cite.confidence >= 0.7 ? "#4ADE80" : cite.confidence >= 0.5 ? "#F5A623" : "#8A96A3",
                }}
              >
                {(cite.confidence * 100).toFixed(0)}%
              </div>
            </div>
            {(cite.section || cite.page_number != null) && (
              <div style={{ fontSize: "10px", color: "#5A6472", marginBottom: "4px", fontFamily: "'IBM Plex Sans', sans-serif" }}>
                {cite.section} {cite.page_number != null ? `(p.${cite.page_number})` : ""}
              </div>
            )}
            <div
              style={{
                fontSize: "11px",
                lineHeight: 1.5,
                color: "#8A96A3",
                fontFamily: "'IBM Plex Sans', sans-serif",
              }}
            >
              &quot;{cite.excerpt}&quot;
            </div>
          </div>
        ))}
      </div>
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            marginTop: "8px",
            background: "none",
            border: "none",
            color: "#3DDBD9",
            fontSize: "10px",
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "'IBM Plex Sans', sans-serif",
            padding: 0,
          }}
        >
          {expanded ? "Show fewer sources" : `Show ${citations.length - 2} more sources`}
        </button>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function ChatPageClient() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  // Persist session ID in ref so it stays constant for the page lifecycle
  const sessionIdRef = useRef<string>("");
  useEffect(() => {
    if (!sessionIdRef.current) {
      sessionIdRef.current = crypto.randomUUID();
    }
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      const q = input.trim();
      if (!q || isLoading) return;

      setInput("");
      const userMsgId = crypto.randomUUID();
      
      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", text: q },
      ]);
      
      setIsLoading(true);

      try {
        const body = {
          question: q,
          session_id: sessionIdRef.current,
          top_k: 5,
          min_score: 0.30,
          expand_graph: false,
        };

        const res = await fetch(`${API_BASE}/api/v1/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text.slice(0, 100)}`);
        }

        const json = await res.json();
        if (json.status === "error") {
           throw new Error(json.message || "Unknown error");
        }
        
        const data = json.data as ChatResponseData;
        const isNoEvidence = data.answer === NO_EVIDENCE_TEXT;

        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: data.answer,
            citations: data.citations,
            confidence: data.confidence,
            isNoEvidence,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "error",
            text: err instanceof Error ? err.message : "An error occurred.",
          },
        ]);
      } finally {
        setIsLoading(false);
        // refocus input slightly after
        setTimeout(() => inputRef.current?.focus(), 50);
      }
    },
    [input, isLoading]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        height: "calc(100vh - 48px)",
        backgroundColor: "#0B0E11",
        fontFamily: "'IBM Plex Sans', sans-serif",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* ── Chat history area ──────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 0" }}>
        <div style={{ maxWidth: "800px", margin: "0 auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: "24px" }}>
          
          {messages.length === 0 && (
            <div style={{ textAlign: "center", marginTop: "10vh", color: "#5A6472" }}>
              <div style={{ fontSize: "32px", marginBottom: "16px" }}>🤖</div>
              <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#E8ECEF", marginBottom: "8px" }}>
                AI Copilot
              </h2>
              <p style={{ fontSize: "13px", maxWidth: "400px", margin: "0 auto", lineHeight: 1.6 }}>
                Ask a question about the industrial knowledge base.
                The copilot will search documents and the knowledge graph to provide an evidence-backed answer.
              </p>
            </div>
          )}

          {messages.map((msg) => {
            if (msg.role === "user") {
              return (
                <div key={msg.id} style={{ alignSelf: "flex-end", maxWidth: "80%" }}>
                  <div
                    style={{
                      backgroundColor: "#1D242B",
                      border: "1px solid #2A333B",
                      borderRadius: "6px 6px 0 6px",
                      padding: "12px 16px",
                      fontSize: "14px",
                      lineHeight: 1.5,
                      color: "#E8ECEF",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {msg.text}
                  </div>
                </div>
              );
            }

            if (msg.role === "error") {
              return (
                <div key={msg.id} style={{ alignSelf: "center", maxWidth: "80%", width: "100%" }}>
                  <div
                    style={{
                      backgroundColor: "rgba(229, 72, 77, 0.1)",
                      border: "1px solid #E5484D",
                      borderRadius: "4px",
                      padding: "12px 16px",
                      fontSize: "13px",
                      color: "#E5484D",
                      textAlign: "center",
                    }}
                  >
                    {msg.text}
                  </div>
                </div>
              );
            }

            // Assistant message
            return (
              <div key={msg.id} style={{ alignSelf: "flex-start", maxWidth: "90%", width: "100%" }}>
                <div
                  style={{
                    backgroundColor: msg.isNoEvidence ? "rgba(245, 166, 35, 0.05)" : "#151A1F",
                    border: `1px solid ${msg.isNoEvidence ? "rgba(245, 166, 35, 0.3)" : "#2A333B"}`,
                    borderRadius: "6px 6px 6px 0",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                    <div
                      style={{
                        width: "20px",
                        height: "20px",
                        borderRadius: "4px",
                        backgroundColor: msg.isNoEvidence ? "#F5A623" : "#3DDBD9",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "10px",
                        color: "#0B0E11",
                        fontWeight: "bold",
                      }}
                    >
                      AI
                    </div>
                    {msg.confidence != null && !msg.isNoEvidence && (
                      <span
                        className="font-mono"
                        style={{
                          fontSize: "10px",
                          color: msg.confidence >= 0.7 ? "#4ADE80" : msg.confidence >= 0.5 ? "#F5A623" : "#8A96A3",
                          border: "1px solid #2A333B",
                          padding: "1px 6px",
                          borderRadius: "2px",
                        }}
                        title="Response Confidence"
                      >
                        {(msg.confidence * 100).toFixed(0)}% CONFIDENCE
                      </span>
                    )}
                    {msg.isNoEvidence && (
                      <span
                        style={{
                          fontSize: "10px",
                          color: "#F5A623",
                          fontWeight: 600,
                          letterSpacing: "0.04em",
                          textTransform: "uppercase",
                        }}
                      >
                        No Evidence Found
                      </span>
                    )}
                  </div>
                  
                  <div
                    style={{
                      fontSize: "14px",
                      lineHeight: 1.6,
                      color: msg.isNoEvidence ? "#8A96A3" : "#E8ECEF",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {msg.text}
                  </div>

                  {!msg.isNoEvidence && msg.citations && msg.citations.length > 0 && (
                    <CitationList citations={msg.citations} />
                  )}
                </div>
              </div>
            );
          })}

          {/* Loading Indicator */}
          {isLoading && (
            <div style={{ alignSelf: "flex-start", maxWidth: "80%" }}>
              <div
                style={{
                  backgroundColor: "#151A1F",
                  border: "1px solid #2A333B",
                  borderRadius: "6px 6px 6px 0",
                  padding: "12px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                }}
              >
                <div
                  style={{
                    width: "16px",
                    height: "16px",
                    border: "2px solid #2A333B",
                    borderTop: "2px solid #3DDBD9",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite",
                  }}
                />
                <span style={{ fontSize: "13px", color: "#5A6472" }}>
                  Analyzing knowledge base... (this can take up to 25s)
                </span>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input area ─────────────────────────────────────────────────── */}
      <div
        style={{
          borderTop: "1px solid #2A333B",
          backgroundColor: "#0B0E11",
          padding: "16px 24px 24px",
        }}
      >
        <form
          onSubmit={handleSubmit}
          style={{
            maxWidth: "800px",
            margin: "0 auto",
            position: "relative",
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={isLoading ? "Please wait for response..." : "Ask the copilot... (Shift+Enter for new line)"}
            style={{
              width: "100%",
              boxSizing: "border-box",
              backgroundColor: "#151A1F",
              border: "1px solid #2A333B",
              borderRadius: "4px",
              padding: "12px 50px 12px 16px",
              fontSize: "14px",
              color: "#E8ECEF",
              fontFamily: "'IBM Plex Sans', sans-serif",
              outline: "none",
              resize: "none",
              minHeight: "52px",
              maxHeight: "150px",
              lineHeight: 1.5,
              overflowY: "auto",
            }}
            rows={1}
            onFocus={(e) => { e.currentTarget.style.borderColor = "#3DDBD9"; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = "#2A333B"; }}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            style={{
              position: "absolute",
              right: "8px",
              bottom: "8px",
              width: "36px",
              height: "36px",
              backgroundColor: isLoading || !input.trim() ? "transparent" : "#3DDBD9",
              color: isLoading || !input.trim() ? "#5A6472" : "#0B0E11",
              border: "none",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: isLoading || !input.trim() ? "not-allowed" : "pointer",
              transition: "all 0.15s",
            }}
            aria-label="Send message"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
