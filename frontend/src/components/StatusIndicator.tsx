import React from "react";
import type { RequestStatus } from "../types";

interface StatusIndicatorProps {
  status: RequestStatus;
}

const STATUS_CONFIG: Record<
  RequestStatus,
  {
    label: string;
    color: string;
    bgColor: string;
    dotColor: string;
  }
> = {
  idle: {
    label: "Ready",
    color: "text-surface-400",
    bgColor: "bg-surface-800",
    dotColor: "bg-surface-500",
  },
  processing: {
    label: "Processing",
    color: "text-primary-400",
    bgColor: "bg-primary-500/10",
    dotColor: "bg-primary-400 animate-pulse",
  },
  success: {
    label: "Success",
    color: "text-success-400",
    bgColor: "bg-success-500/10",
    dotColor: "bg-success-500",
  },
  error: {
    label: "Error",
    color: "text-danger-400",
    bgColor: "bg-danger-500/10",
    dotColor: "bg-danger-500",
  },
};

export default function StatusIndicator({ status }: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status];

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${config.bgColor}`}>
      <div className={`w-2 h-2 rounded-full ${config.dotColor}`} />
      <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
    </div>
  );
}
