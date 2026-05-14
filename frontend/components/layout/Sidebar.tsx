"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Bell,
  CheckSquare,
  AlertTriangle,
  BarChart3,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 bg-black/40 border-r border-white/8 flex flex-col relative z-10">
      {/* Logo */}
      <div className="px-5 py-4 border-b border-white/8">
        <div className="flex items-center gap-2.5">
          <Image
            src="/tg-logo.svg"
            alt="TruGlobal"
            width={34}
            height={34}
            className="rounded-full shadow-lg shadow-blue-500/25 shrink-0"
          />
          <div>
            <p className="text-sm font-bold text-white leading-none">TG OPS AI</p>
            <p className="text-[10px] text-gray-500 mt-0.5">Intelligence Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href}>
              <div className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 group relative",
                active
                  ? "bg-white/10 text-white font-medium"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              )}>
                {active && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-500 rounded-full"
                  />
                )}
                <Icon className={cn("w-4 h-4", active ? "text-blue-400" : "text-gray-500 group-hover:text-gray-300")} />
                {item.label}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Pipeline trigger */}
      <div className="px-3 pb-4">
        <div className="rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-white/10 p-3">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-medium text-white">AI Pipeline</span>
          </div>
          <p className="text-[10px] text-gray-500 mb-2">LangGraph multi-agent orchestration</p>
          <PipelineTrigger />
        </div>
      </div>
    </aside>
  );
}

const PIPELINE_STAGES = [
  { min: 0,  max: 4,  label: "Connecting to TG database…", pct: 15 },
  { min: 4,  max: 10, label: "Fetching 60-day data…",      pct: 35 },
  { min: 10, max: 18, label: "Running AI agents…",          pct: 55 },
  { min: 18, max: 26, label: "Detecting risks & SLAs…",     pct: 70 },
  { min: 26, max: 34, label: "Generating executive summary…",pct: 82 },
  { min: 34, max: 50, label: "Persisting to database…",     pct: 92 },
  { min: 50, max: 999,label: "Finalising…",                 pct: 97 },
];

function PipelineTrigger() {
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [stage, setStage] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");

  const trigger = async () => {
    if (status === "running") return;
    setStatus("running");
    setStage(0);
    const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    try {
      const res = await fetch(`${BASE}/pipeline/trigger`, { method: "POST" });
      if (!res.ok) throw new Error("trigger failed");
      const { run_id } = await res.json();

      let attempts = 0;
      while (attempts < 150) {
        await new Promise((r) => setTimeout(r, 3000));
        attempts++;
        // Update stage indicator
        const stageIdx = PIPELINE_STAGES.findIndex(
          (s) => attempts >= s.min && attempts < s.max
        );
        if (stageIdx >= 0) setStage(stageIdx);

        try {
          const statusRes = await fetch(`${BASE}/pipeline/status/${run_id}`);
          if (!statusRes.ok) continue;
          const info = await statusRes.json();
          if (info.status === "COMPLETED") {
            setStatus("done");
            setTimeout(() => window.location.reload(), 1000);
            return;
          } else if (info.status === "FAILED") {
            setStatus("error");
            setErrorMsg(info.error?.slice(0, 70) ?? "Pipeline failed");
            setTimeout(() => { setStatus("idle"); setErrorMsg(""); }, 7000);
            return;
          }
        } catch { /* ignore poll errors */ }
      }
      // Timeout — reload anyway
      setStatus("done");
      setTimeout(() => window.location.reload(), 1000);
    } catch {
      setStatus("error");
      setErrorMsg("Could not reach backend");
      setTimeout(() => { setStatus("idle"); setErrorMsg(""); }, 5000);
    }
  };

  const currentStage = PIPELINE_STAGES[stage] ?? PIPELINE_STAGES[0];

  return (
    <div className="space-y-2">
      <button
        onClick={trigger}
        disabled={status === "running"}
        className={cn(
          "w-full text-xs py-2 rounded-lg font-semibold transition-all px-2.5",
          status === "running"
            ? "bg-blue-500/20 text-blue-300 cursor-not-allowed"
            : status === "done"
            ? "bg-emerald-500/20 text-emerald-300"
            : status === "error"
            ? "bg-red-500/20 text-red-300"
            : "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 active:scale-[0.98]"
        )}
      >
        {status === "running" ? (
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse shrink-0" />
            Running…
          </span>
        ) : status === "done" ? (
          "✓ Done — reloading page"
        ) : status === "error" ? (
          "✗ Failed — click to retry"
        ) : (
          "▶  Run Analysis"
        )}
      </button>

      {/* Progress bar + stage label */}
      {status === "running" && (
        <div className="space-y-1">
          <div className="h-1 rounded-full bg-white/8 overflow-hidden">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-700"
              style={{ width: `${currentStage.pct}%` }}
            />
          </div>
          <p className="text-[9px] text-blue-400/80 leading-tight">{currentStage.label}</p>
        </div>
      )}

      {/* Error message */}
      {status === "error" && errorMsg && (
        <p className="text-[9px] text-red-400/80 leading-tight break-all">{errorMsg}</p>
      )}
    </div>
  );
}
