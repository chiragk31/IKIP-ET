"use client";

/**
 * DashboardHeader
 *
 * Platform-wide navigation header for the dashboard.
 * Industrial control-room style: dark graphite, no decorative gradients.
 */

import Link from "next/link";
import { Activity, Database, Search, MessageSquare, LayoutDashboard, FileText } from "lucide-react";

interface DashboardHeaderProps {
  lastUpdated?: Date;
}

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents/upload", label: "Documents", icon: FileText },
  { href: "/graph", label: "Graph", icon: Database },
  { href: "/search", label: "Search", icon: Search },
  { href: "/chat", label: "Copilot", icon: MessageSquare },
] as const;

export function DashboardHeader({ lastUpdated }: DashboardHeaderProps) {
  const ts = lastUpdated
    ? lastUpdated.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : null;

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
      {/* Logo mark */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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
          <Activity
            size={14}
            style={{ color: "#3DDBD9" }}
            aria-hidden="true"
          />
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
      </div>

      {/* Navigation */}
      <nav
        style={{
          display: "flex",
          alignItems: "center",
          gap: "2px",
        }}
        aria-label="Platform navigation"
      >
        {NAV_LINKS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "5px 10px",
              fontSize: "12px",
              fontWeight: 500,
              letterSpacing: "0.02em",
              color: "#8A96A3",
              textDecoration: "none",
              borderRadius: "2px",
              transition: "color 0.1s, background-color 0.1s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#E8ECEF";
              e.currentTarget.style.backgroundColor = "#1D242B";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#8A96A3";
              e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            <Icon size={12} aria-hidden="true" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Last updated timestamp */}
      {ts && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "5px",
            fontSize: "10px",
            color: "#5A6472",
          }}
        >
          <span
            style={{
              width: "5px",
              height: "5px",
              borderRadius: "50%",
              backgroundColor: "#4ADE80",
              boxShadow: "0 0 4px #4ADE80",
              animation: "none",
            }}
            aria-hidden="true"
          />
          <span className="font-mono">LIVE · {ts}</span>
        </div>
      )}
    </header>
  );
}
