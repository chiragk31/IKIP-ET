"use client";

/**
 * AppHeader — Single shared platform header, mounted once in layout.tsx.
 *
 * Appears on every route. Active nav item is highlighted via usePathname().
 * Visual style is lifted exactly from the original dashboard-header.tsx:
 *   - Dark canvas (#0B0E11) background, 1px border-bottom
 *   - IBM Plex Sans, 48px height, sticky top-0
 *   - IKIP logo mark (Activity icon + wordmark) on the left
 *   - 5 nav items in the centre
 *   - Live dot on the right
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Database,
  Search,
  MessageSquare,
  LayoutDashboard,
  FileText,
} from "lucide-react";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/graph", label: "Graph", icon: Database },
  { href: "/search", label: "Search", icon: Search },
  { href: "/chat", label: "Copilot", icon: MessageSquare },
] as const;

/** Returns true when the nav link should be considered "active". */
function isActive(navHref: string, pathname: string): boolean {
  return pathname === navHref || pathname.startsWith(navHref + "/");
}

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header
      style={{
        backgroundColor: "#0B0E11",
        borderBottom: "1px solid #2A333B",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        height: "48px",
        flexShrink: 0,
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      {/* ── Logo mark ─────────────────────────────────────── */}
      <Link
        href="/"
        style={{ display: "flex", alignItems: "center", gap: "10px", textDecoration: "none" }}
        aria-label="IKIP home"
      >
        <div
          style={{
            width: "28px",
            height: "28px",
            backgroundColor: "#1D242B",
            border: "1px solid #2A333B",
            borderRadius: "2px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Activity size={14} style={{ color: "#3DDBD9" }} aria-hidden="true" />
        </div>
        <div>
          <span
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "13px",
              fontWeight: 600,
              letterSpacing: "0.04em",
              color: "#E8ECEF",
            }}
          >
            IKIP
          </span>
          <span
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "10px",
              letterSpacing: "0.08em",
              color: "#5A6472",
              marginLeft: "6px",
              textTransform: "uppercase",
            }}
          >
            Industrial Knowledge Intelligence
          </span>
        </div>
      </Link>

      {/* ── Navigation ────────────────────────────────────── */}
      <nav
        style={{ display: "flex", alignItems: "center", gap: "2px" }}
        aria-label="Platform navigation"
      >
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const active = isActive(href, pathname);
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                padding: "5px 10px",
                fontSize: "12px",
                fontWeight: active ? 600 : 500,
                letterSpacing: "0.02em",
                color: active ? "#E8ECEF" : "#8A96A3",
                textDecoration: "none",
                borderRadius: "2px",
                backgroundColor: active ? "#1D242B" : "transparent",
                transition: "color 0.1s, background-color 0.1s",
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  e.currentTarget.style.color = "#E8ECEF";
                  e.currentTarget.style.backgroundColor = "#1D242B";
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  e.currentTarget.style.color = "#8A96A3";
                  e.currentTarget.style.backgroundColor = "transparent";
                }
              }}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={12} aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* ── Live indicator ────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "5px",
          fontSize: "10px",
          color: "#5A6472",
        }}
        aria-label="System live"
      >
        <span
          style={{
            width: "5px",
            height: "5px",
            borderRadius: "50%",
            backgroundColor: "#4ADE80",
            boxShadow: "0 0 4px #4ADE80",
          }}
          aria-hidden="true"
        />
        <span className="font-mono">LIVE</span>
      </div>
    </header>
  );
}
