import React, { useEffect, useState } from "react";
import { api } from "../api";
import type { SchemaDetail } from "../types";

interface SchemaViewerProps {
  schemaName: string;
  rawData?: Record<string, unknown> | null;
}

function getValueType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function isMatch(value: unknown, expectedType: string): boolean {
  const actualType = getValueType(value);
  const normalizedExpected = expectedType.toLowerCase();
  if (normalizedExpected.includes("str")) return actualType === "string";
  if (normalizedExpected.includes("int") || normalizedExpected.includes("float")) return actualType === "number";
  if (normalizedExpected.includes("bool")) return actualType === "boolean";
  if (normalizedExpected.includes("list") || normalizedExpected.includes("array")) return actualType === "array";
  if (normalizedExpected.includes("dict") || normalizedExpected.includes("object") || normalizedExpected.includes("model")) return actualType === "object";
  return true;
}

export default function SchemaViewer({ schemaName, rawData }: SchemaViewerProps) {
  const [schema, setSchema] = useState<SchemaDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadSchema() {
      setLoading(true);
      try {
        const result = await api.getSchema(schemaName);
        setSchema(result);
      } catch {
        // ignore
      }
      setLoading(false);
    }
    loadSchema();
  }, [schemaName]);

  if (loading) {
    return (
      <div className="card p-8 flex items-center justify-center">
        <div className="flex items-center gap-3 text-surface-400">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading schema...
        </div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="card p-8 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-xl bg-surface-800 flex items-center justify-center text-2xl mb-3">
          📋
        </div>
        <p className="text-surface-400">Schema details not available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Schema Header */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-white">{schema.name}</h3>
            <p className="text-sm text-surface-400 mt-0.5">{schema.description}</p>
          </div>
          <span className="badge-info">{schema.field_count} fields</span>
        </div>
      </div>

      {/* Expected vs Actual */}
      <div className="card overflow-hidden">
        <div className="px-4 py-3 bg-surface-900/50 border-b border-surface-700/30">
          <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider">
            Field Validation
          </h4>
        </div>
        <div className="divide-y divide-surface-800">
          {Object.entries(schema.fields).map(([fieldName, fieldInfo]) => {
            const actualValue = rawData?.[fieldName];
            const hasData = rawData !== undefined && rawData !== null;
            const expectedType = fieldInfo.type;
            const typeMatches = hasData ? isMatch(actualValue, expectedType) : null;
            const isRequired = fieldInfo.required;
            const valuePresent = hasData && actualValue !== undefined;
            const isValid = isRequired ? valuePresent && typeMatches : true;

            return (
              <div
                key={fieldName}
                className="px-4 py-3 flex items-start gap-3 hover:bg-surface-800/30 transition-colors duration-150"
              >
                {/* Status Dot */}
                <div className="mt-1.5">
                  {hasData ? (
                    <div className={`w-2 h-2 rounded-full ${
                      isValid ? "bg-success-500" : "bg-danger-500"
                    }`} />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-surface-600" />
                  )}
                </div>

                {/* Field Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <code className="text-sm font-mono text-primary-400">{fieldName}</code>
                    <span className="text-xs text-surface-500 font-mono">{expectedType.replace("typing.", "").replace("<class '", "").replace("'>", "")}</span>
                    {isRequired && <span className="badge-danger text-[10px] px-1.5 py-0.5">required</span>}
                    {!isRequired && <span className="badge text-[10px] px-1.5 py-0.5 bg-surface-700 text-surface-400 border border-surface-600">optional</span>}
                  </div>
                  {fieldInfo.description && (
                    <p className="text-xs text-surface-500 mt-0.5">{fieldInfo.description}</p>
                  )}
                  {fieldInfo.default && (
                    <p className="text-xs text-surface-500 mt-0.5">
                      Default: <code className="text-surface-400">{fieldInfo.default}</code>
                    </p>
                  )}
                </div>

                {/* Actual Value */}
                <div className="text-right">
                  {hasData && actualValue !== undefined ? (
                    <>
                      <span className={`text-xs font-mono block ${
                        isValid ? "text-success-400" : "text-danger-400"
                      }`}>
                        {typeof actualValue === "object"
                          ? `[${getValueType(actualValue)}]`
                          : String(actualValue).slice(0, 30)}
                      </span>
                      <span className="text-[10px] text-surface-500">
                        {getValueType(actualValue)}
                      </span>
                    </>
                  ) : (
                    <span className="text-xs text-surface-500">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Schema Summary */}
      {rawData && (
        <div className="card p-4">
          <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-3">
            Validation Summary
          </h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-surface-800/50 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-success-400">
                {Object.entries(schema.fields).filter(([name]) => rawData[name] !== undefined).length}
              </div>
              <p className="text-xs text-surface-400 mt-1">Fields Present</p>
            </div>
            <div className="bg-surface-800/50 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-danger-400">
                {Object.entries(schema.fields).filter(([name]) => rawData[name] === undefined && schema.fields[name].required).length}
              </div>
              <p className="text-xs text-surface-400 mt-1">Missing Required</p>
            </div>
            <div className="bg-surface-800/50 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-primary-400">{schema.field_count}</div>
              <p className="text-xs text-surface-400 mt-1">Total Defined</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
