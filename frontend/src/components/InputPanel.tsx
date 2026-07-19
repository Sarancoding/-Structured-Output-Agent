import React from "react";
import type { ProcessRequest } from "../types";
import { SCHEMA_OPTIONS } from "../types";

interface InputPanelProps {
  query: string;
  onQueryChange: (query: string) => void;
  generator: string;
  onGeneratorChange: (generator: ProcessRequest["generator"]) => void;
  schema: string;
  onSchemaChange: (schema: string) => void;
  onProcess: () => void;
  isProcessing: boolean;
}

const GENERATOR_OPTIONS = [
  { value: "mock_success", label: "Standard (Success)", description: "Valid output on first try", color: "text-success-400" },
  { value: "mock_fail_once", label: "Retry Once", description: "Fails then succeeds", color: "text-warning-400" },
  { value: "mock_always_fails", label: "Always Fails", description: "All attempts fail", color: "text-danger-400" },
];

export default function InputPanel({
  query,
  onQueryChange,
  generator,
  onGeneratorChange,
  schema,
  onSchemaChange,
  onProcess,
  isProcessing,
}: InputPanelProps) {
  return (
    <div className="glass-panel p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-1">
          Query Input
        </h2>
        <p className="text-xs text-surface-500 mb-3">
          Enter the text you want the agent to analyze
        </p>
        <textarea
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Enter your query here..."
          rows={4}
          className="input-field resize-none"
          disabled={isProcessing}
        />
      </div>

      <div>
        <label className="text-xs font-medium text-surface-400 uppercase tracking-wider mb-2 block">
          Generator Mode
        </label>
        <div className="space-y-1.5">
          {GENERATOR_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onGeneratorChange(opt.value as ProcessRequest["generator"])}
              disabled={isProcessing}
              className={`w-full text-left px-3 py-2.5 rounded-lg border transition-all duration-200 ${
                generator === opt.value
                  ? "bg-primary-500/10 border-primary-500/30 text-white"
                  : "bg-surface-800/50 border-surface-700/30 text-surface-400 hover:border-surface-600 hover:text-surface-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{opt.label}</span>
                <span className={`text-xs font-mono ${opt.color}`}>●</span>
              </div>
              <p className="text-xs text-surface-500 mt-0.5">{opt.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-surface-400 uppercase tracking-wider mb-2 block">
          Output Schema
        </label>
        <div className="relative">
          <select
            value={schema}
            onChange={(e) => onSchemaChange(e.target.value)}
            disabled={isProcessing}
            className="input-field appearance-none cursor-pointer pr-10"
          >
            {SCHEMA_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-surface-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>

      <button
        onClick={onProcess}
        disabled={isProcessing || !query.trim()}
        className={`btn-primary w-full flex items-center justify-center gap-2 ${
          isProcessing ? "animate-pulse" : ""
        }`}
      >
        {isProcessing ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Processing...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Execute
          </>
        )}
      </button>
    </div>
  );
}
