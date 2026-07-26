/**
 * WidgetError — Error state for dashboard widgets
 *
 * One widget failing must never block others.
 * This component renders an inline error that keeps the widget slot visible.
 */

import { AlertTriangle } from "lucide-react";

interface WidgetErrorProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function WidgetError({
  title = "Unable to load data",
  message = "Service may be temporarily unavailable.",
  onRetry,
}: WidgetErrorProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 p-6 text-center"
      style={{ color: "#8A96A3" }}
    >
      <AlertTriangle
        size={20}
        style={{ color: "#F5A623" }}
        aria-hidden="true"
      />
      <div>
        <p
          className="text-sm font-medium"
          style={{ color: "#E8ECEF" }}
        >
          {title}
        </p>
        <p className="text-xs mt-1">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs px-3 py-1.5 border transition-colors hover-elevate"
          style={{
            color: "#3DDBD9",
            borderColor: "#2A333B",
            backgroundColor: "#151A1F",
            borderRadius: "2px",
          }}
        >
          Retry
        </button>
      )}
    </div>
  );
}
