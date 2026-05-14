"use client";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Play, Database } from "lucide-react";
import { getDashboardSummary, type DashboardData } from "@/lib/api";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { ExecutiveSummary } from "@/components/dashboard/ExecutiveSummary";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { AccountRiskHeatmap } from "@/components/dashboard/AccountRiskHeatmap";
import { RecruiterStats } from "@/components/dashboard/RecruiterStats";
import { Button } from "@/components/ui/button";

const EMPTY_KPIS: DashboardData["kpis"] = {
  open_positions: 0, total_submissions: 0, aging_critical: 0,
  aging_at_risk: 0, no_shows: 0, budget_mismatch: 0,
  tech_rejections: 0, on_hold: 0,
};

const EMPTY_TREND: DashboardData["trend_data"] = {
  weeks: [], sla_breaches: [], no_shows: [], tech_rejections: [], open_positions: [],
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDashboardSummary();
      // Only set data if we got a real pipeline run (run_id is present)
      if (result?.run_id) {
        setData(result);
        setLastFetched(new Date().toISOString());
      } else {
        setData(null);
      }
    } catch {
      setError("Could not reach backend");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const hasData = !!data?.run_id;

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-xl font-bold text-white">Operational Overview</h2>
            {hasData && (
              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-[10px] text-blue-400 font-medium">
                Last 60 days
              </span>
            )}
          </div>
          {lastFetched ? (
            <p className="text-xs text-gray-500 mt-0.5" suppressHydrationWarning>
              Refreshed:{" "}
              {new Date(lastFetched).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" })}
              {data?.generated_at && (
                <span className="ml-1.5 text-gray-600">
                  · Pipeline ran{" "}
                  {new Date(data.generated_at).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" })}
                </span>
              )}
              {error && <span className="ml-2 text-amber-400">{error}</span>}
            </p>
          ) : (
            <p className="text-xs text-gray-500 mt-0.5">
              {loading ? "Loading pipeline data…" : "No pipeline data yet — use Run Analysis in the sidebar to begin"}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Empty state */}
      {!loading && !hasData && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-white/10 bg-white/2 text-center"
        >
          <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4">
            <Database className="w-7 h-7 text-blue-400" />
          </div>
          <h3 className="text-base font-semibold text-white mb-1">No pipeline data yet</h3>
          <p className="text-sm text-gray-500 max-w-sm mb-5">
            Click <strong className="text-gray-300">Run Analysis</strong> in the sidebar to fetch live data from
            the TG database, run the AI pipeline, and populate the dashboard.
          </p>
          <div className="flex items-center gap-1.5 text-xs text-gray-600">
            <Play className="w-3 h-3" />
            The pipeline also runs automatically every day at 06:00 UTC
          </div>
        </motion.div>
      )}

      {/* Live data */}
      {hasData && data && (
        <>
          <KpiCards
            kpis={data.kpis ?? EMPTY_KPIS}
            activeAlerts={data.active_alerts ?? 0}
            pendingApprovals={data.pending_approvals ?? 0}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <ExecutiveSummary
                summary={data.executive_summary ?? ""}
                highlights={data.executive_highlights ?? []}
                generatedAt={data.generated_at ?? new Date().toISOString()}
              />
            </div>
            <div className="lg:col-span-2">
              {(data.trend_data?.weeks?.length ?? 0) > 0 ? (
                <TrendChart data={data.trend_data} />
              ) : (
                <div className="h-full flex items-center justify-center rounded-2xl border border-white/8 bg-white/2">
                  <p className="text-xs text-gray-600">Trend data available after multiple runs</p>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AccountRiskHeatmap data={data.account_risk_scores ?? []} />
            <RecruiterStats data={data.recruiter_stats ?? []} />
          </div>
        </>
      )}
    </div>
  );
}
