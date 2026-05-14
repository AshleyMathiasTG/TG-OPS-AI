"use client";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Bell, CheckCheck, RefreshCw } from "lucide-react";
import { getNotifications, markNotificationsRead, type Notification } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime } from "@/lib/utils";

const priorityBadge: Record<string, string> = {
  CRITICAL: "critical",
  WARNING: "warning",
  INFO: "info",
};

const priorityBorder: Record<string, string> = {
  CRITICAL: "border-l-red-500",
  WARNING: "border-l-amber-500",
  INFO: "border-l-blue-500",
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getNotifications();
      setNotifications(result ?? []);
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const markAllRead = async () => {
    const ids = notifications.filter((n) => !n.is_read).map((n) => n.id);
    if (ids.length) {
      await markNotificationsRead(ids).catch(() => {});
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    }
  };

  const filtered =
    filter === "All"
      ? notifications
      : filter === "Unread"
      ? notifications.filter((n) => !n.is_read)
      : notifications.filter((n) => n.priority === filter);

  const unread = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="max-w-2xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Bell className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-bold text-white">Notification Center</h2>
            {unread > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold">
                {unread} new
              </span>
            )}
            {notifications.length > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] text-gray-400 font-medium">
                Last 60 days
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {loading
              ? "Loading…"
              : notifications.length === 0
              ? "No notifications in the last 60 days"
              : `${notifications.length} notification${notifications.length !== 1 ? "s" : ""} from pipeline runs`}
          </p>
        </div>
        <div className="flex gap-2">
          {unread > 0 && (
            <Button variant="outline" size="sm" onClick={markAllRead}>
              <CheckCheck className="w-3 h-3" /> Mark all read
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={load} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Filter tabs — only when there are notifications */}
      {notifications.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {["All", "Unread", "CRITICAL", "WARNING", "INFO"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                filter === f ? "bg-white/15 text-white" : "bg-white/5 text-gray-500 hover:bg-white/10"
              }`}
            >
              {f}
              {f !== "All" && f !== "Unread" && (
                <span className="ml-1 text-[10px] opacity-60">
                  {notifications.filter((n) => n.priority === f).length}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {!loading && notifications.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-white/10 bg-white/2 text-center"
        >
          <Bell className="w-10 h-10 text-gray-700 mb-3" />
          <p className="text-sm font-medium text-gray-400">No notifications yet</p>
          <p className="text-xs text-gray-600 mt-1">
            Notifications are created when the pipeline runs and detects issues.
          </p>
        </motion.div>
      ) : (
        <div className="space-y-2">
          {filtered.length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-10">No notifications in this category</p>
          ) : (
            filtered.map((n, i) => (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className={`flex gap-3 p-4 rounded-xl border border-l-2 transition-opacity ${
                  priorityBorder[n.priority]
                } ${!n.is_read ? "bg-white/4 border-white/10 opacity-100" : "bg-white/2 border-white/6 opacity-55"}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    {!n.is_read && (
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 animate-pulse" />
                    )}
                    <Badge variant={priorityBadge[n.priority] as any} className="text-[9px] px-1.5 py-0">
                      {n.priority}
                    </Badge>
                    <span className="text-[10px] text-gray-600 ml-auto">{formatRelativeTime(n.created_at)}</span>
                  </div>
                  <p className={`text-sm font-medium leading-snug ${!n.is_read ? "text-white" : "text-gray-400"}`}>
                    {n.title}
                  </p>
                  {n.body && (
                    <p className="text-xs text-gray-500 mt-1 leading-relaxed">{n.body}</p>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
