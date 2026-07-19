import React from "react";
import { GENERATOR_PRESETS } from "../types";

interface DemoPresetsProps {
  onSelect: (presetId: string) => void;
  activePreset: string;
}

export default function DemoPresets({ onSelect, activePreset }: DemoPresetsProps) {
  return (
    <div className="glass-panel p-5">
      <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-1">
        Demo Scenarios
      </h2>
      <p className="text-xs text-surface-500 mb-4">
        Quick-select preset configurations to test different agent behaviors
      </p>

      <div className="space-y-2.5">
        {GENERATOR_PRESETS.map((preset) => {
          const isActive = activePreset === preset.generator;
          return (
            <button
              key={preset.id}
              onClick={() => onSelect(preset.id)}
              className={`w-full text-left p-3 rounded-xl border transition-all duration-200 ${
                isActive
                  ? "bg-primary-500/10 border-primary-500/30 shadow-sm shadow-primary-500/10"
                  : "bg-surface-800/40 border-surface-700/30 hover:border-surface-600 hover:bg-surface-800/60"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl mt-0.5">{preset.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className={`text-sm font-semibold ${
                      isActive ? "text-primary-300" : "text-surface-200"
                    }`}>
                      {preset.label}
                    </h3>
                    {isActive && (
                      <span className="text-[10px] font-medium text-primary-400 bg-primary-500/20 px-2 py-0.5 rounded-full">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-surface-500 mt-0.5">{preset.description}</p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
