/**
 * API client for TG OPS AI backend.
 * All requests go through this module for consistent error handling.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Dashboard ──────────────────────────────────────────────────────────────

export const getDashboardSummary = () =>
  apiFetch<DashboardData>("/dashboard/summary");

export const getDashboardSnapshots = (limit = 10) =>
  apiFetch<SnapshotRow[]>(`/dashboard/snapshots?limit=${limit}`);

// ── Alerts ────────────────────────────────────────────────────────────────

export const getAlerts = (params?: { severity?: string; is_read?: boolean }) => {
  const qs = new URLSearchParams();
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.is_read !== undefined) qs.set("is_read", String(params.is_read));
  return apiFetch<Alert[]>(`/alerts?${qs}`);
};

export const markAlertsRead = (ids: string[]) =>
  apiFetch("/alerts/mark-read", { method: "PATCH", body: JSON.stringify({ ids }) });

export const dismissAlert = (id: string) =>
  apiFetch(`/alerts/${id}`, { method: "DELETE" });

// ── Approvals ──────────────────────────────────────────────────────────────

export const getApprovals = (status?: string) =>
  apiFetch<Approval[]>(`/approvals${status ? `?status=${status}` : ""}`);

export const decideApproval = (id: string, status: "APPROVED" | "REJECTED", note?: string) =>
  apiFetch(`/approvals/${id}/decide`, {
    method: "PATCH",
    body: JSON.stringify({ status, reviewer_note: note }),
  });

export const submitFeedback = (approvalId: string, sentiment: "THUMBS_UP" | "THUMBS_DOWN", comment?: string) =>
  apiFetch(`/approvals/${approvalId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ sentiment, comment }),
  });

// ── Notifications ─────────────────────────────────────────────────────────

export const getNotifications = (params?: { priority?: string; is_read?: boolean }) => {
  const qs = new URLSearchParams();
  if (params?.priority) qs.set("priority", params.priority);
  if (params?.is_read !== undefined) qs.set("is_read", String(params.is_read));
  return apiFetch<Notification[]>(`/notifications?${qs}`);
};

export const getUnreadCount = () =>
  apiFetch<{ unread: number }>("/notifications/unread-count");

export const markNotificationsRead = (ids: string[]) =>
  apiFetch("/notifications/mark-read", { method: "PATCH", body: JSON.stringify({ ids }) });

// ── Analytics ─────────────────────────────────────────────────────────────

export const getAnalyticsOverview = () =>
  apiFetch<AnalyticsData>("/analytics/overview");

export const getRiskHeatmap = () =>
  apiFetch<AccountRisk[]>("/analytics/risk-heatmap");

// ── Pipeline ──────────────────────────────────────────────────────────────

export const triggerPipeline = () =>
  apiFetch<{ run_id: string; status: string; message: string }>("/pipeline/trigger", { method: "POST" });

export const getPipelineStatus = (runId: string) =>
  apiFetch<PipelineRun>(`/pipeline/status/${runId}`);

export const listPipelineRuns = () =>
  apiFetch<{ run_id: string; status: string; started_at: string }[]>("/pipeline/runs");

// ── Type definitions ──────────────────────────────────────────────────────

export interface DashboardData {
  run_id: string;
  executive_summary: string;
  executive_highlights: string[];
  kpis: {
    open_positions: number;
    total_submissions: number;
    aging_critical: number;
    aging_at_risk: number;
    no_shows: number;
    budget_mismatch: number;
    tech_rejections: number;
    on_hold: number;
  };
  account_risk_scores: AccountRisk[];
  recruiter_stats: RecruiterStat[];
  trend_data: TrendData;
  active_alerts: number;
  pending_approvals: number;
  generated_at: string;
}

export interface AccountRisk {
  account: string;
  score: number;
  submissions: number;
  no_shows: number;
  rejections: number;
  aging_critical: number;
}

export interface RecruiterStat {
  recruiter: string;
  active: number;
  no_shows: number;
  rejections: number;
}

export interface TrendData {
  weeks: string[];
  sla_breaches: number[];
  no_shows: number[];
  tech_rejections: number[];
  open_positions: number[];
}

export interface Alert {
  id: string;
  run_id: string;
  alert_type: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  title: string;
  summary?: string;
  entity_name?: string;
  is_read: boolean;
  is_dismissed: boolean;
  created_at: string;
}

export interface Approval {
  id: string;
  recommendation_id: string;
  run_id: string;
  issue_summary: string;
  recommended_action: string;
  escalation_path?: string;
  mitigation_steps?: string;
  impact_level?: string;
  confidence_score?: number;
  status: "PENDING" | "APPROVED" | "REJECTED";
  reviewer_note?: string;
  decided_at?: string;
  created_at: string;
}

export interface Notification {
  id: string;
  run_id?: string;
  priority: "INFO" | "WARNING" | "CRITICAL";
  channel: string;
  title: string;
  body?: string;
  is_read: boolean;
  created_at: string;
}

export interface AnalyticsData {
  status_distribution: Record<string, number>;
  risk_by_account: { account: string; score: number; label: string }[];
  recruiter_performance: {
    recruiter: string;
    active: number;
    no_shows: number;
    rejections: number;
    load_score: number;
  }[];
  trend: TrendData & { budget_mismatch: number[] };
  top_issues: { type: string; count: number; trend: string }[];
}

export interface SnapshotRow {
  run_id: string;
  open_risks: number;
  sla_breaches: number;
  active_alerts: number;
  pending_approvals: number;
  created_at: string;
}

export interface PipelineRun {
  run_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  error?: string;
  summary?: string;
  risk_count: number;
  approval_count: number;
}
