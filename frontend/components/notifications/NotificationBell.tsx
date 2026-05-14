"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, X, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getNotifications, getUnreadCount, markNotificationsRead, type Notification } from "@/lib/api";
import { formatRelativeTime, severityBg } from "@/lib/utils";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);

  const load = async () => {
    try {
      const [notifs, count] = await Promise.all([getNotifications(), getUnreadCount()]);
      setNotifications(notifs);
      setUnread(count.unread);
    } catch {
      // fallback silently
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const markAllRead = async () => {
    const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
    if (unreadIds.length) {
      await markNotificationsRead(unreadIds);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    }
  };

  const priorityBadge: Record<string, string> = {
    CRITICAL: "critical",
    WARNING: "warning",
    INFO: "info",
  };

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen(!open)}
        className="relative"
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-white text-[9px] flex items-center justify-center font-bold">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </Button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 mt-2 w-96 z-50 bg-gray-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <span className="text-sm font-semibold text-white">Notifications</span>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={markAllRead} className="text-xs h-7">
                    <CheckCheck className="w-3 h-3 mr-1" /> Mark all read
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setOpen(false)} className="h-7 w-7">
                    <X className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>

              <div className="max-h-96 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="text-center text-gray-500 text-sm py-8">No notifications</p>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors ${
                        !n.is_read ? "bg-white/3" : ""
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {!n.is_read && (
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <Badge variant={priorityBadge[n.priority] as any} className="text-[10px] px-1.5 py-0">
                              {n.priority}
                            </Badge>
                            <span className="text-[10px] text-gray-500">{formatRelativeTime(n.created_at)}</span>
                          </div>
                          <p className="text-xs text-white font-medium leading-snug">{n.title}</p>
                          {n.body && (
                            <p className="text-[11px] text-gray-400 mt-0.5 leading-snug line-clamp-2">{n.body}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
