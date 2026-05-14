"use client";
import { useEffect, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { RefreshCw, AlertTriangle, Bell } from "lucide-react";
import { getAlerts, markAlertsRead, type Alert } from "@/lib/api";
import { AlertItem } from "@/components/alerts/AlertItem";
import { Button } from "@/components/ui/button";

const severityFilters = ["All", "CRITICAL", "WARNING", "INFO"];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAlerts();
      setAlerts(result ?? []);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const handleDismiss = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const handleMarkAllRead = async () => {
    const ids = alerts.filter((a) => !a.is_read).map((a) => a.id);
    if (ids.length) {
      await markAlertsRead(ids).catch(() => {});
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
    }
  };

  const filtered = filter === "All" ? alerts : alerts.filter((a) => a.severity === filter);
  const unreadCount = alerts.filter((a) => !a.is_read).length;

  return (
    <div className="max-w-3xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <h2 className="text-xl font-bold text-white">Active Alerts</h2>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-xs font-semibold">
                {unreadCount} unread
              </span>
            )}
            {alerts.length > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] text-gray-400 font-medium">
                Last 60 days
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {loading ? "Loading…" : alerts.length === 0
              ? "No alerts in the last 60 days"
              : `${alerts.length} alert${alerts.length !== 1 ? "s" : ""} in the last 60 days`}
          </p>
        </div>
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
              Mark all read
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={loadAlerts} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Severity filters — only show when there are alerts */}
      {alerts.length > 0 && (
        <div className="flex gap-2">
          {severityFilters.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                filter === f
                  ? "bg-white/15 text-white"
                  : "bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300"
              }`}
            >
              {f}
              {f !== "All" && (
                <span className="ml-1 text-[10px] opacity-70">
                  {alerts.filter((a) => a.severity === f).length}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {!loading && alerts.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-white/10 bg-white/2 text-center"
        >
          <Bell className="w-10 h-10 text-gray-700 mb-3" />
          <p className="text-sm font-medium text-gray-400">No alerts detected</p>
          <p className="text-xs text-gray-600 mt-1">
            Alerts are generated when the pipeline detects operational issues.
          </p>
        </motion.div>
      ) : (
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {filtered.length === 0 ? (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center text-gray-500 text-sm py-10"
              >
                No alerts matching this filter
              </motion.p>
            ) : (
              filtered.map((alert, i) => (
                <AlertItem key={alert.id} alert={alert} index={i} onDismiss={handleDismiss} />
              ))
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
