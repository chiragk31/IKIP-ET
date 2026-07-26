"use client";

/**
 * HomePageClient — Landing page interactive content.
 *
 * Extracted into a client component so that onMouseEnter/onMouseLeave
 * event handlers are legal (Server Components cannot accept event props).
 * page.tsx stays as a Server Component to own the Metadata export.
 */

import Link from "next/link";

const FEATURES = [
  {
    icon: "📄",
    title: "Document Processing",
    description:
      "Upload PDFs, DOCX, XLSX, and images. AI automatically parses, OCR-processes, and extracts structured knowledge.",
    accent: "#3DDBD9",
  },
  {
    icon: "🧠",
    title: "Knowledge Graph",
    description:
      "Discover assets, people, events, and relationships across all your documents in Neo4j — automatically.",
    accent: "#F5A623",
  },
  {
    icon: "🔍",
    title: "Semantic Search",
    description:
      "Search using natural language. Find relevant document chunks via Gemini embeddings and Pinecone vector search.",
    accent: "#3DDBD9",
  },
  {
    icon: "🤖",
    title: "AI Copilot",
    description:
      'Ask questions like "Why did Pump P101 fail?" and get evidence-backed answers with citations.',
    accent: "#F5A623",
  },
  {
    icon: "⚙️",
    title: "Asset 360",
    description:
      "Every discovered asset gets an automatic profile: maintenance history, measurements, and relationship map.",
    accent: "#3DDBD9",
  },
  {
    icon: "✅",
    title: "Compliance Intelligence",
    description:
      "Detect missing inspections, expired certificates, and compliance gaps automatically.",
    accent: "#F5A623",
  },
] as const;

export function HomePageClient() {
  return (
    <main
      style={{
        minHeight: "calc(100vh - 48px)",
        backgroundColor: "#0B0E11",
        fontFamily: "'IBM Plex Sans', sans-serif",
        color: "#E8ECEF",
      }}
    >
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section
        style={{
          maxWidth: "900px",
          margin: "0 auto",
          padding: "80px 24px 64px",
          textAlign: "center",
        }}
        aria-label="Platform overview"
      >
        {/* Badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "7px",
            padding: "4px 10px",
            border: "1px solid #2A333B",
            borderRadius: "3px",
            backgroundColor: "#151A1F",
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#8A96A3",
            marginBottom: "36px",
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "1px",
              backgroundColor: "#3DDBD9",
              boxShadow: "0 0 4px #3DDBD9",
              flexShrink: 0,
            }}
            aria-hidden="true"
          />
          AI-Powered Industrial Intelligence
        </div>

        {/* Headline */}
        <h1
          style={{
            fontSize: "clamp(36px, 6vw, 60px)",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
            marginBottom: "24px",
          }}
        >
          Your Industrial{" "}
          <span
            style={{
              backgroundImage: "linear-gradient(90deg, #F5A623 0%, #3DDBD9 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Knowledge Brain
          </span>
        </h1>

        {/* Sub-headline */}
        <p
          style={{
            fontSize: "16px",
            lineHeight: 1.7,
            color: "#8A96A3",
            maxWidth: "620px",
            margin: "0 auto 48px",
          }}
        >
          Transform maintenance reports, SOPs, inspection records, and engineering
          documents into structured organizational intelligence. Semantic search,
          knowledge graph, and AI Copilot — all powered by your own documents.
        </p>

        {/* CTA buttons */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
            justifyContent: "center",
          }}
        >
          <Link
            href="/documents/upload"
            id="hero-upload-btn"
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "10px 24px",
              backgroundColor: "#F5A623",
              color: "#0B0E11",
              fontSize: "13px",
              fontWeight: 700,
              letterSpacing: "0.02em",
              borderRadius: "3px",
              textDecoration: "none",
              border: "1px solid #F5A623",
              transition: "opacity 0.15s",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.opacity = "0.88"; }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; }}
          >
            Upload Documents
          </Link>

          <Link
            href="/chat"
            id="hero-copilot-btn"
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "10px 24px",
              backgroundColor: "transparent",
              color: "#E8ECEF",
              fontSize: "13px",
              fontWeight: 600,
              letterSpacing: "0.02em",
              borderRadius: "3px",
              textDecoration: "none",
              border: "1px solid #2A333B",
              transition: "border-color 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#3DDBD9";
              e.currentTarget.style.color = "#3DDBD9";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#2A333B";
              e.currentTarget.style.color = "#E8ECEF";
            }}
          >
            Ask AI Copilot
          </Link>

          <Link
            href="/dashboard"
            id="hero-dashboard-btn"
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "10px 24px",
              backgroundColor: "transparent",
              color: "#8A96A3",
              fontSize: "13px",
              fontWeight: 500,
              letterSpacing: "0.02em",
              borderRadius: "3px",
              textDecoration: "none",
              border: "1px solid #2A333B",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#E8ECEF"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#8A96A3"; }}
          >
            View Dashboard →
          </Link>
        </div>
      </section>

      {/* ── Separator ─────────────────────────────────────────────────────── */}
      <div
        style={{ height: "1px", backgroundColor: "#2A333B", margin: "0 24px" }}
        aria-hidden="true"
      />

      {/* ── Feature grid ──────────────────────────────────────────────────── */}
      <section
        style={{ maxWidth: "1100px", margin: "0 auto", padding: "64px 24px 80px" }}
        aria-label="Platform capabilities"
      >
        <p
          style={{
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#5A6472",
            marginBottom: "32px",
          }}
        >
          Platform Capabilities
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: "1px",
            backgroundColor: "#2A333B",
          }}
        >
          {FEATURES.map((f) => (
            <div
              key={f.title}
              style={{ backgroundColor: "#151A1F", padding: "24px", transition: "background-color 0.1s" }}
              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "#1D242B"; }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#151A1F"; }}
            >
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "36px",
                  height: "36px",
                  borderRadius: "3px",
                  backgroundColor: `${f.accent}18`,
                  border: `1px solid ${f.accent}40`,
                  fontSize: "18px",
                  marginBottom: "16px",
                }}
                aria-hidden="true"
              >
                {f.icon}
              </div>
              <h3
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "#E8ECEF",
                  marginBottom: "8px",
                  letterSpacing: "0.01em",
                }}
              >
                {f.title}
              </h3>
              <p style={{ fontSize: "12px", lineHeight: 1.65, color: "#8A96A3" }}>
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "1px solid #2A333B",
          padding: "20px 24px",
          textAlign: "center",
          fontSize: "11px",
          color: "#5A6472",
          fontFamily: "'IBM Plex Mono', monospace",
          letterSpacing: "0.04em",
        }}
      >
        IKIP · INDUSTRIAL KNOWLEDGE INTELLIGENCE PLATFORM · BUILT FOR INDUSTRIAL TEAMS
      </footer>
    </main>
  );
}
