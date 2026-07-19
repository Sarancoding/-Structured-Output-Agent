import React from "react";

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

interface LogViewerProps {
  logs: LogEntry[];
}

function getLevelStyle(level: string): string {
  switch (level) {
    case "ERROR":
    case "CRITICAL":
      return "text-danger-400 bg-danger-500/10";
    case "WARNING":
      return "text-warning-400 bg-warning-500/10";
    case "INFO":
      return "text-primary-400 bg-primary-500/10";
    case "DEBUG":
      return "text-surface-500 bg-surface-800";
    default:
      return "text-surface-400 bg-surface-800";
  }
}

function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    const hh = String(date.getHours()).padStart(2, "0");
    const mm = String(date.getMinutes()).padStart(2, "0");
    const ss = String(date.getSeconds()).padStart(2, "0");
    const ms = String(date.getMilliseconds()).padStart(3, "0");
    return `${hh}:${mm}:${ss}.${ms}`;
  } catch {
    return isoString;
  }
}

export default function LogViewer({ logs }: LogViewerProps) {
  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-surface-900/50 border-b border-surface-700/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider">
            Event Log
          </h4>
          {logs.length > 0 && (
            <span className="text-xs text-surface-500">({logs.length} entries)</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {["ERROR", "WARNING", "INFO"].map((level) => {
            const count = logs.filter((l) => l.level === level).length;
            if (count === 0) return null;
            return (
              <span
                key={level}
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${getLevelStyle(level)}`}
              >
                {count}
              </span>
            );
          })}
        </div>
      </div>

      {/* Log Entries */}
      <div className="max-h-[400px] overflow-y-auto">
        {logs.length === 0 ? (
          <div className="p-8 text-center text-surface-500 text-sm">
            <p className="mb-1">No log entries yet</p>
            <p className="text-xs">Execute a request to see structured log output</p>
          </div>
        ) : (
          <div className="font-mono text-xs">
            {logs.map((entry, index) => (
              <div
                key={index}
                className={`flex items-start gap-3 px-4 py-2 hover:bg-surface-800/30 transition-colors duration-150 ${
                  entry.level === "ERROR"
                    ? "bg-danger-500/5"
                    : entry.level === "WARNING"
                    ? "bg-warning-500/5"
                    : ""
                }`}
              >
                <span className="text-surface-500 whitespace-nowrap pt-0.5" title={entry.timestamp}>
                  {formatTimestamp(entry.timestamp)}
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded font-bold whitespace-nowrap shrink-0 ${
                    entry.level === "ERROR"
                      ? "text-danger-400"
                      : entry.level === "WARNING"
                      ? "text-warning-400"
                      : "text-primary-400"
                  }`}
                >
                  {entry.level.padEnd(8)}
                </span>
                <span className="text-surface-300 break-words min-w-0">
                  {entry.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
