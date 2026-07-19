import type {
  ProcessRequest,
  ProcessResponse,
  AgentStats,
  SchemaInfo,
  SchemaDetail,
  GeneratorInfo,
  HistoryEntry,
  LogResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const config: RequestInit = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  /* ─── Processing ──────────────────────────────────────────────────── */

  process(data: ProcessRequest): Promise<ProcessResponse> {
    return request<ProcessResponse>("/process", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  validateRaw(rawData: Record<string, unknown>, schema: string) {
    return request("/validate", {
      method: "POST",
      body: JSON.stringify({ raw_data: rawData, schema }),
    });
  },

  /* ─── Schemas ─────────────────────────────────────────────────────── */

  getSchemas(): Promise<{ schemas: SchemaInfo[]; count: number }> {
    return request("/schemas");
  },

  getSchema(name: string): Promise<SchemaDetail> {
    return request(`/schemas/${name}`);
  },

  /* ─── Generators ──────────────────────────────────────────────────── */

  getGenerators(): Promise<{ generators: GeneratorInfo[]; count: number }> {
    return request("/generators");
  },

  /* ─── History & Stats ─────────────────────────────────────────────── */

  getHistory(limit = 10, status?: string): Promise<{ history: HistoryEntry[]; total: number }> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status) params.set("status", status);
    return request(`/history?${params}`);
  },

  getStats(): Promise<AgentStats> {
    return request("/stats");
  },

  /* ─── Logs ────────────────────────────────────────────────────────── */

  getLogs(level?: string, limit = 100, requestId?: string): Promise<LogResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (level) params.set("level", level);
    if (requestId) params.set("request_id", requestId);
    return request(`/logs?${params}`);
  },

  /* ─── Config ──────────────────────────────────────────────────────── */

  reset(): Promise<{ status: string }> {
    return request("/reset", { method: "POST" });
  },

  updateConfig(config: Record<string, unknown>): Promise<{ status: string; config: Record<string, unknown> }> {
    return request("/config", {
      method: "POST",
      body: JSON.stringify(config),
    });
  },
};
