/* ─── API Types ─────────────────────────────────────────────────────────── */

export interface ProcessRequest {
  query?: string;
  generator: "mock_success" | "mock_fail_once" | "mock_always_fails";
  schema: string;
  context?: Record<string, unknown>;
}

export interface AttemptDetail {
  attempt: number;
  timestamp: string;
  error: string;
  success: boolean;
}

export interface ProcessResponse {
  request_id: string;
  success: boolean;
  data: Record<string, unknown> | null;
  error: Record<string, unknown> | string | null;
  validation_status: "success" | "failure" | "warning" | "retrying" | "fallback";
  retry_attempts: number;
  attempt_details: AttemptDetail[];
  processing_time_ms: number;
  schema_used: string;
  timestamp: string;
}

export interface ValidateRequest {
  raw_data: Record<string, unknown>;
  schema: string;
}

export interface SchemaInfo {
  name: string;
  description: string;
  fields: string[];
}

export interface SchemaDetail {
  name: string;
  description: string;
  fields: Record<
    string,
    {
      type: string;
      required: boolean;
      default: string | null;
      description: string;
    }
  >;
  field_count: number;
}

export interface GeneratorInfo {
  name: string;
  module: string;
  type: "mock" | "custom";
}

export interface HistoryEntry {
  request_id: string;
  timestamp: string;
  schema: string;
  success: boolean;
  status: string;
  attempts: number;
  processing_time_ms: number;
}

export interface AgentStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_processing_time_ms: number;
  retry_handler_stats: Record<string, unknown>;
  available_schemas: string[];
  available_generators: string[];
}

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  [key: string]: unknown;
}

export interface LogResponse {
  entries: LogEntry[];
  count: number;
  stats: Record<string, unknown>;
}

/* ─── Frontend State Types ───────────────────────────────────────────── */

export type RequestStatus = "idle" | "processing" | "success" | "error";

export type GeneratorPreset = {
  id: string;
  label: string;
  description: string;
  generator: ProcessRequest["generator"];
  icon: string;
};

export const GENERATOR_PRESETS: GeneratorPreset[] = [
  {
    id: "success",
    label: "Standard Success",
    description: "Generates valid structured output on first try",
    generator: "mock_success",
    icon: "✅",
  },
  {
    id: "fail-once",
    label: "Retry Once",
    description: "Fails first validation, succeeds on retry",
    generator: "mock_fail_once",
    icon: "🔄",
  },
  {
    id: "always-fails",
    label: "Always Fails",
    description: "Fails all validation attempts, returns fallback",
    generator: "mock_always_fails",
    icon: "❌",
  },
];

export const SCHEMA_OPTIONS = [
  { value: "TextAnalysis", label: "Text Analysis" },
  { value: "SentimentAnalysis", label: "Sentiment Analysis" },
  { value: "Entity", label: "Entity" },
  { value: "KeyPoint", label: "Key Point" },
  { value: "ActionItem", label: "Action Item" },
];
