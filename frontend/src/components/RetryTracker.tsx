import React from "react";
import type { AttemptDetail } from "../types";

interface RetryTrackerProps {
  attempts: AttemptDetail[];
}

function formatTime(isoString: string): string {
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

export default function RetryTracker({ attempts }: RetryTrackerProps) {
  const failedAttempts = attempts.filter((a) => !a.success);
  if (failedAttempts.length === 0) return null;

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 bg-surface-900/50 border-b border-surface-700/30 flex items-center justify-between">
        <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider">
          Retry Attempts
        </h4>
        <span className="badge-warning">
          {failedAttempts.length} failed
        </span>
      </div>

      <div className="divide-y divide-surface-800">
        {attempts.map((attempt, index) => (
          <div
            key={index}
            className={`px-4 py-3 transition-colors duration-150 ${
              attempt.success
                ? "hover:bg-surface-800/20"
                : "hover:bg-danger-500/5"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
                  attempt.success
                    ? "bg-success-500/10 text-success-400"
                    : "bg-danger-500/10 text-danger-400"
                }`}>
                  {attempt.attempt + 1}
                </span>
                <span className="text-sm font-medium text-surface-300">
                  {attempt.success ? "Succeeded" : "Failed"}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-surface-500">
                <span>{formatTime(attempt.timestamp)}</span>

              </div>
            </div>

            {attempt.error && !attempt.success && (
              <p className="text-xs text-danger-400 font-mono ml-8 bg-surface-950/50 rounded px-2 py-1.5 overflow-x-auto">
                {attempt.error}
              </p>
            )}

            {/* Timeline Bar */}
            <div className="mt-2 ml-8">
              <div className="h-1.5 rounded-full bg-surface-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${
                    attempt.success
                      ? "bg-gradient-to-r from-success-500 to-success-400"
                      : "bg-gradient-to-r from-danger-500 to-danger-400"
                  }`}
                  style={{
                    width: attempt.success ? "100%" : attempt.attempt < attempts.length - 1 ? "60%" : "100%",
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
