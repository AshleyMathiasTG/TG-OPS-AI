import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function severityColor(severity: string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL": return "text-red-500";
    case "WARNING": return "text-amber-500";
    case "INFO": return "text-blue-500";
    default: return "text-gray-500";
  }
}

export function severityBg(severity: string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL": return "bg-red-500/10 border-red-500/20 text-red-400";
    case "WARNING": return "bg-amber-500/10 border-amber-500/20 text-amber-400";
    case "INFO": return "bg-blue-500/10 border-blue-500/20 text-blue-400";
    default: return "bg-gray-500/10 border-gray-500/20 text-gray-400";
  }
}

export function impactColor(level: string): string {
  switch (level?.toUpperCase()) {
    case "CRITICAL": return "text-red-500";
    case "HIGH": return "text-orange-500";
    case "MEDIUM": return "text-amber-500";
    case "LOW": return "text-green-500";
    default: return "text-gray-400";
  }
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export function truncate(str: string, length: number): string {
  if (!str) return "";
  return str.length > length ? `${str.slice(0, length)}…` : str;
}
