"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { RefreshCw, Calendar, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";

const pageTitles: Record<string, string> = {
  "/":             "Operational Dashboard",
  "/alerts":       "Active Alerts",
  "/approvals":    "Approval Center",
  "/notifications":"Notification Center",
  "/analytics":    "Analytics & Insights",
};

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function TopBar() {
  const pathname = usePathname();
  const title = pageTitles[pathname] ?? "TG OPS AI";

  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [fixtureMode, setFixtureMode] = useState<boolean | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(BASE.replace("/api/v1", "/health"));
        if (res.ok) {
          const data = await res.json();
          setBackendOk(true);
          setFixtureMode(data.fixture_mode ?? false);
        } else {
          setBackendOk(false);
        }
      } catch {
        setBackendOk(false);
      }
    };
    check();
  }, []);

  return (
    <header className="h-14 shrink-0 border-b border-white/8 bg-black/20 backdrop-blur-sm flex items-center justify-between px-6 relative z-10">
      <div>
        <h1 className="text-sm font-semibold text-white">{title}</h1>
        <p className="text-[10px] text-gray-500">TG OPS AI — AI-Powered Operational Intelligence</p>
      </div>

      <div className="flex items-center gap-2">
        {/* Data window badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/8">
          <Calendar className="w-3 h-3 text-gray-500" />
          <span className="text-[10px] text-gray-400 font-medium">Last 60 days</span>
        </div>

        {/* Fixture mode warning */}
        {fixtureMode && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
            <span className="text-[10px] text-amber-400 font-medium">Fixture Mode</span>
          </div>
        )}

        {/* Backend status */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${
          backendOk === null
            ? "bg-white/5 border-white/8"
            : backendOk
            ? "bg-emerald-500/10 border-emerald-500/20"
            : "bg-red-500/10 border-red-500/20"
        }`}>
          {backendOk === null ? (
            <div className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-pulse" />
          ) : backendOk ? (
            <Wifi className="w-3 h-3 text-emerald-400" />
          ) : (
            <WifiOff className="w-3 h-3 text-red-400" />
          )}
          <span className={`text-[10px] font-medium ${
            backendOk === null ? "text-gray-500" : backendOk ? "text-emerald-400" : "text-red-400"
          }`}>
            {backendOk === null ? "Checking…" : backendOk ? "Connected" : "Offline"}
          </span>
        </div>

        <NotificationBell />

        <Button variant="ghost" size="icon" onClick={() => window.location.reload()}>
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>
    </header>
  );
}
