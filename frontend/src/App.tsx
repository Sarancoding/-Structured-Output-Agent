import React, { useState, useCallback, useRef, useEffect } from "react";
import type { ProcessRequest, ProcessResponse, RequestStatus } from "./types";
import { GENERATOR_PRESETS, SCHEMA_OPTIONS } from "./types";
import { api } from "./api";
import InputPanel from "./components/InputPanel";
import OutputDisplay from "./components/OutputDisplay";
import SchemaViewer from "./components/SchemaViewer";
import StatusIndicator from "./components/StatusIndicator";
import RetryTracker from "./components/RetryTracker";
import LogViewer from "./components/LogViewer";
import DemoPresets from "./components/DemoPresets";
import ExportButton from "./components/ExportButton";

export default function App() {
  const [query, setQuery] = useState("Analyze the impact of artificial intelligence on modern healthcare.");
  const [generator, setGenerator] = useState<ProcessRequest["generator"]>("mock_success");
  const [schema, setSchema] = useState("TextAnalysis");
  const [status, setStatus] = useState<RequestStatus>("idle");
  const [response, setResponse] = useState<ProcessResponse | null>(null);
  const [logs, setLogs] = useState<Array<{ timestamp: string; level: string; message: string }>>([]);
  const [activeTab, setActiveTab] = useState<"response" | "schema" | "logs">("response");
  const outputRef = useRef<HTMLDivElement>(null);

  const handleProcess = useCallback(async () => {
    setStatus("processing");
    setResponse(null);
    addLog("info", "Processing request...");

    try {
      const result = await api.process({
        query,
        generator,
        schema,
        context: { source: "demo-ui" },
      });

      setResponse(result);
      setStatus(result.success ? "success" : "error");

      if (result.success) {
        addLog("info", `Request completed successfully (${result.processing_time_ms.toFixed(1)}ms, ${result.retry_attempts} retries)`);
      } else {
        addLog("error", `Request failed with status: ${result.validation_status}`);
      }

      // Log retry details
      result.attempt_details.forEach((attempt) => {
        if (!attempt.success) {
          addLog("warning", `Attempt ${attempt.attempt + 1} failed: ${attempt.error}`);
        }
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      addLog("error", `Request error: ${message}`);
      setStatus("error");
    }
  }, [query, generator, schema]);

  const handleReset = useCallback(async () => {
    try {
      await api.reset();
    } catch {
      // ignore
    }
    setResponse(null);
    setStatus("idle");
    setLogs([]);
  }, []);

  const addLog = useCallback((level: string, message: string) => {
    setLogs((prev) => [
      {
        timestamp: new Date().toISOString(),
        level: level.toUpperCase(),
        message,
      },
      ...prev.slice(0, 99),
    ]);
  }, []);

  const handlePresetSelect = useCallback(
    (presetId: string) => {
      const preset = GENERATOR_PRESETS.find((p) => p.id === presetId);
      if (preset) {
        setGenerator(preset.generator);
        addLog("info", `Switched to generator: ${preset.label}`);
      }
    },
    [addLog]
  );

  // Scroll to results when response comes in
  useEffect(() => {
    if (response && outputRef.current) {
      outputRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [response]);

  return (
    <div className="min-h-screen bg-surface-950">
      {/* Header */}
      <header className="border-b border-surface-800 bg-surface-950/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-lg shadow-lg shadow-primary-500/20">
                🧠
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Structured Output Agent</h1>
                <p className="text-xs text-surface-400">Demo Interface</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusIndicator status={status} />
              <ExportButton response={response} logs={logs} />
              <button onClick={handleReset} className="btn-ghost text-sm" title="Reset state">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Input & Controls */}
          <div className="lg:col-span-1 space-y-4">
            <InputPanel
              query={query}
              onQueryChange={setQuery}
              generator={generator}
              onGeneratorChange={setGenerator}
              schema={schema}
              onSchemaChange={setSchema}
              onProcess={handleProcess}
              isProcessing={status === "processing"}
            />

            <DemoPresets onSelect={handlePresetSelect} activePreset={generator} />
          </div>

          {/* Right Column - Output */}
          <div className="lg:col-span-2 space-y-4" ref={outputRef}>
            {/* Tabs */}
            <div className="flex gap-1 bg-surface-900/50 rounded-xl p-1 border border-surface-700/30">
              {(["response", "schema", "logs"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    activeTab === tab
                      ? "bg-surface-800 text-white shadow-sm"
                      : "text-surface-400 hover:text-surface-200"
                  }`}
                >
                  {tab === "response" ? "📄 Response" : tab === "schema" ? "📋 Schema" : "📝 Logs"}
                </button>
              ))}
            </div>

            {/* Response Tab */}
            {activeTab === "response" && (
              <div className="space-y-4">
                <OutputDisplay response={response} status={status} />
                {response && response.retry_attempts > 0 && (
                  <RetryTracker attempts={response.attempt_details} />
                )}
              </div>
            )}

            {/* Schema Tab */}
            {activeTab === "schema" && (
              <SchemaViewer schemaName={schema} rawData={response?.data} />
            )}

            {/* Logs Tab */}
            {activeTab === "logs" && <LogViewer logs={logs} />}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-800 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between text-sm text-surface-500">
            <span>Structured Output Agent v1.0.0</span>
            <div className="flex items-center gap-4">
              <span>FastAPI + React + TypeScript</span>
              <span className="w-2 h-2 rounded-full bg-success-500 animate-pulse-slow" />
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
