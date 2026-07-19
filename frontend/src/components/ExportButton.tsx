import React, { useRef, useState } from "react";
import type { ProcessResponse } from "../types";

interface ExportButtonProps {
  response: ProcessResponse | null;
  logs: Array<{ timestamp: string; level: string; message: string }>;
}

export default function ExportButton({ response, logs }: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  function downloadJSON(data: unknown, filename: string) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Close on click outside
  React.useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [open]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        disabled={!response && logs.length === 0}
        className="btn-ghost text-sm"
        title="Export data"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-52 bg-surface-800 border border-surface-700 rounded-xl shadow-2xl shadow-black/50 z-50 overflow-hidden animate-fade-in">
          <div className="p-2 space-y-0.5">
            <button
              onClick={() => {
                if (response) {
                  downloadJSON(response, `agent-response-${response.request_id}.json`);
                }
                setOpen(false);
              }}
              disabled={!response}
              className="w-full text-left px-3 py-2.5 rounded-lg text-sm text-surface-300 hover:bg-surface-700 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              📄 Export Response
            </button>
            <button
              onClick={() => {
                if (logs.length > 0) {
                  downloadJSON(logs, "agent-logs.json");
                }
                setOpen(false);
              }}
              disabled={logs.length === 0}
              className="w-full text-left px-3 py-2.5 rounded-lg text-sm text-surface-300 hover:bg-surface-700 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              📝 Export Logs
            </button>
            <button
              onClick={() => {
                if (response && logs.length > 0) {
                  downloadJSON(
                    { response, logs, exportedAt: new Date().toISOString() },
                    "agent-full-export.json"
                  );
                }
                setOpen(false);
              }}
              disabled={!response || logs.length === 0}
              className="w-full text-left px-3 py-2.5 rounded-lg text-sm text-surface-300 hover:bg-surface-700 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              📦 Export All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
