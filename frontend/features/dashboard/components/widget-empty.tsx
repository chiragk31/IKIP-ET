/**
 * WidgetEmpty — Empty state for dashboard widgets
 *
 * Communicates system status rather than appearing unfinished.
 */

import { Inbox } from "lucide-react";

interface WidgetEmptyProps {
  message?: string;
  action?: string;
  onAction?: () => void;
}

export function WidgetEmpty({
  message = "No data available.",
  action,
  onAction,
}: WidgetEmptyProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 p-6 text-center"
      style={{ color: "#8A96A3" }}
    >
      <Inbox size={20} aria-hidden="true" />
      <p className="text-xs">{message}</p>
      {action && onAction && (
        <button
          onClick={onAction}
          className="text-xs px-3 py-1.5 border transition-colors"
          style={{
            color: "#3DDBD9",
            borderColor: "#2A333B",
            backgroundColor: "#151A1F",
            borderRadius: "2px",
          }}
        >
          {action}
        </button>
      )}
    </div>
  );
}
