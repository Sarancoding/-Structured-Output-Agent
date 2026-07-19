import React from "react";
import type { ProcessResponse, RequestStatus } from "../types";

interface OutputDisplayProps {
  response: ProcessResponse | null;
  status: RequestStatus;
}

function highlightJSON(obj: unknown, indent = 0): React.ReactNode {
  const indentStr = "  ".repeat(indent);

  if (obj === null || obj === undefined) {
    return <span className="json-null">null</span>;
  }

  if (typeof obj === "string") {
    return <span className="json-string">"{obj}"</span>;
  }

  if (typeof obj === "number") {
    return <span className="json-number">{obj}</span>;
  }

  if (typeof obj === "boolean") {
    return <span className="json-boolean">{obj.toString()}</span>;
  }

  if (Array.isArray(obj)) {
    if (obj.length === 0) return <span className="text-surface-500">[]</span>;
    return (
      <>
        <span className="text-surface-400">[</span>
        <br />
        {obj.map((item, i) => (
          <React.Fragment key={i}>
            <span className="text-surface-400">{indentStr}  </span>
            {highlightJSON(item, indent + 1)}
            {i < obj.length - 1 && <span className="text-surface-500">,</span>}
            <br />
          </React.Fragment>
        ))}
        <span className="text-surface-400">{indentStr}]</span>
      </>
    );
  }

  if (typeof obj === "object") {
    const entries = Object.entries(obj as Record<string, unknown>);
    if (entries.length === 0) return <span className="text-surface-500">{`{}`}</span>;
    return (
      <>
        <span className="text-surface-400">{`{`}</span>
        <br />
        {entries.map(([key, value], i) => (
          <React.Fragment key={key}>
            <span className="text-surface-400">{indentStr}  </span>
            <span className="json-key">"{key}"</span>
            <span className="text-surface-500">: </span>
            {highlightJSON(value, indent + 1)}
            {i < entries.length - 1 && <span className="text-surface-500">,</span>}
            <br />
          </React.Fragment>
        ))}
        <span className="text-surface-400">{indentStr}{`}`}</span>
      </>
    );
  }

  return <span>{String(obj)}</span>;
}

export default function OutputDisplay({ response, status }: OutputDisplayProps) {
  if (status === "idle") {
    return (
      <div className="card p-12 flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center text-3xl mb-4">
          🚀
        </div>
        <h3 className="text-lg font-semibold text-surface-300 mb-2">Ready to Process</h3>
        <p className="text-sm text-surface-500 max-w-md">
          Enter a query, select a generator mode and schema, then click Execute to see the structured output.
        </p>
      </div>
    );
  }

  if (status === "processing") {
    return (
      <div className="card p-12 flex flex-col items-center justify-center">
        <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mb-4">
          <svg className="animate-spin h-8 w-8 text-primary-400" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-surface-300 mb-2">Processing...</h3>
        <p className="text-sm text-surface-500">Running validation pipeline with retry logic.</p>
      </div>
    );
  }

  if (!response) {
    return null;
  }

  return (
    <div className="space-y-3">
      {/* Metadata Bar */}
      <div className="card p-4 flex flex-wrap items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-surface-500">Request ID:</span>
          <code className="text-xs font-mono text-primary-400 bg-primary-500/10 px-2 py-0.5 rounded">
            {response.request_id.slice(0, 12)}...
          </code>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-surface-500">Schema:</span>
          <span className="badge-info">{response.schema_used}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-surface-500">Time:</span>
          <code className="text-xs font-mono text-surface-300">
            {response.processing_time_ms.toFixed(1)}ms
          </code>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-surface-500">Retries:</span>
          <code className="text-xs font-mono text-surface-300">
            {response.retry_attempts}
          </code>
        </div>
      </div>

      {/* Status Banner */}
      <div className={`card p-4 flex items-center gap-3 border-l-4 ${
        response.success
          ? "border-l-success-500"
          : response.validation_status === "fallback"
          ? "border-l-warning-500"
          : "border-l-danger-500"
      }`}>
        <span className="text-2xl">
          {response.success ? "✅" : response.validation_status === "fallback" ? "⚠️" : "❌"}
        </span>
        <div>
          <p className="font-medium text-white">
            {response.success
              ? "Validation Successful"
              : response.validation_status === "fallback"
              ? "Fallback Response (all retries exhausted)"
              : "Validation Failed"}
          </p>
          <p className="text-xs text-surface-400">
            Status: {response.validation_status}
            {response.retry_attempts > 0 && ` · ${response.retry_attempts} retr${response.retry_attempts === 1 ? "y" : "ies"}`}
          </p>
        </div>
      </div>

      {/* JSON Output */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-surface-900/50 border-b border-surface-700/30">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-surface-600" />
            <span className="text-xs font-medium text-surface-400">Structured Output</span>
          </div>
        </div>
        <pre className="code-block m-0 rounded-none text-sm leading-relaxed max-h-96 overflow-y-auto">
          <code className="font-mono">
            {highlightJSON((response.data ?? response.error) as Record<string, unknown>)}
          </code>
        </pre>
      </div>

      {/* Error Details */}
      {!response.success && response.error && (
        <div className="card p-4 border-l-4 border-l-danger-500">
          <h4 className="text-sm font-semibold text-danger-400 mb-2">Error Details</h4>
          {typeof response.error === "object" && response.error !== null ? (
            <pre className="text-xs text-surface-400 max-h-40 overflow-y-auto">
              {JSON.stringify(response.error, null, 2) ?? ""}
            </pre>
          ) : (
            <p className="text-sm text-surface-400">{String(response.error)}</p>
          )}
        </div>
      )}
    </div>
  );
}
