"use client";
import { motion } from "framer-motion";
import { AlertTriangle, Activity, Bell, CheckCircle2, TrendingUp, Users, Clock, XCircle } from "lucide-react";
import type { DashboardData } from "@/lib/api";

interface KpiCardsProps {
  kpis: DashboardData["kpis"];
  activeAlerts: number;
  pendingApprovals: number;
}

const kpiConfig = [
  {
    key: "open_positions",
    label: "Open Positions",
    icon: Activity,
    value_color: "text-blue-300",
    accent: "from-blue-500/15 to-blue-500/5",
    dot: "bg-blue-500",
    border: "border-blue-500/15",
  },
  {
    key: "aging_critical",
    label: "SLA Breaches",
    icon: Clock,
    value_color: "text-red-300",
    accent: "from-red-500/15 to-red-500/5",
    dot: "bg-red-500",
    border: "border-red-500/20",
    critical_if: (v: number) => v > 0,
  },
  {
    key: "activeAlerts",
    label: "Active Alerts",
    icon: Bell,
    value_color: "text-amber-300",
    accent: "from-amber-500/15 to-amber-500/5",
    dot: "bg-amber-500",
    border: "border-amber-500/15",
    critical_if: (v: number) => v > 5,
  },
  {
    key: "pendingApprovals",
    label: "Pending Approvals",
    icon: CheckCircle2,
    value_color: "text-purple-300",
    accent: "from-purple-500/15 to-purple-500/5",
    dot: "bg-purple-500",
    border: "border-purple-500/15",
  },
  {
    key: "no_shows",
    label: "Interview No-Shows",
    icon: XCircle,
    value_color: "text-rose-300",
    accent: "from-rose-500/15 to-rose-500/5",
    dot: "bg-rose-500",
    border: "border-rose-500/15",
    critical_if: (v: number) => v >= 3,
  },
  {
    key: "budget_mismatch",
    label: "Budget Mismatches",
    icon: TrendingUp,
    value_color: "text-orange-300",
    accent: "from-orange-500/15 to-orange-500/5",
    dot: "bg-orange-500",
    border: "border-orange-500/15",
  },
  {
    key: "tech_rejections",
    label: "Tech Rejections",
    icon: AlertTriangle,
    value_color: "text-yellow-300",
    accent: "from-yellow-500/15 to-yellow-500/5",
    dot: "bg-yellow-500",
    border: "border-yellow-500/15",
  },
  {
    key: "aging_at_risk",
    label: "At-Risk Submissions",
    icon: Users,
    value_color: "text-cyan-300",
    accent: "from-cyan-500/15 to-cyan-500/5",
    dot: "bg-cyan-500",
    border: "border-cyan-500/15",
  },
];

export function KpiCards({ kpis, activeAlerts, pendingApprovals }: KpiCardsProps) {
  const values: Record<string, number> = { ...kpis, activeAlerts, pendingApprovals };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {kpiConfig.map((item, index) => {
        const Icon = item.icon;
        const value = values[item.key] ?? 0;
        const isCritical = item.critical_if?.(value) ?? false;

        return (
          <motion.div
            key={item.key}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.35 }}
          >
            <div className={`relative rounded-xl border ${item.border} bg-gradient-to-br ${item.accent} p-4 overflow-hidden`}>
              {isCritical && (
                <span className="absolute top-2.5 right-2.5 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${item.dot}`} />
                </span>
              )}
              <div className="flex items-center gap-2 mb-3">
                <div className={`p-1.5 rounded-lg bg-white/5`}>
                  <Icon className={`w-3.5 h-3.5 ${item.value_color}`} />
                </div>
                <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide leading-none">
                  {item.label}
                </p>
              </div>
              <p className={`text-2xl font-bold ${item.value_color} tabular-nums`}>{value}</p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
