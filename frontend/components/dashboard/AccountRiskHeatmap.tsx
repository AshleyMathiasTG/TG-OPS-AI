"use client";
import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { AccountRisk } from "@/lib/api";

interface AccountRiskHeatmapProps {
  data: AccountRisk[];
}

function getRiskMeta(score: number) {
  if (score >= 10) return { label: "CRITICAL", text: "text-red-400", bar: "bg-red-500", badge: "bg-red-500/15 text-red-400 border-red-500/20" };
  if (score >= 6)  return { label: "HIGH",     text: "text-orange-400", bar: "bg-orange-500", badge: "bg-orange-500/15 text-orange-400 border-orange-500/20" };
  if (score >= 3)  return { label: "MEDIUM",   text: "text-amber-400",  bar: "bg-amber-500",  badge: "bg-amber-500/15 text-amber-400 border-amber-500/20"  };
  return              { label: "LOW",      text: "text-emerald-400", bar: "bg-emerald-500", badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20" };
}

export function AccountRiskHeatmap({ data }: AccountRiskHeatmapProps) {
  const maxScore = Math.max(...(data ?? []).map((d) => d.score), 1);
  const safeData = data ?? [];

  return (
    <Card className="border-white/10">
      <CardHeader className="pb-3 px-5 pt-5">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <CardTitle className="text-sm font-semibold">Account Risk Heatmap</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="px-5 pb-5">
        {safeData.length === 0 ? (
          <p className="text-center text-gray-600 text-xs py-8">No account data available</p>
        ) : (
          <div className="space-y-4">
            {safeData.map((account, i) => {
              const meta = getRiskMeta(account.score);
              const pct = Math.max((account.score / maxScore) * 100, 3);
              return (
                <motion.div
                  key={account.account}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06 }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold text-gray-200">{account.account}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-600">{account.submissions} subs</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${meta.badge}`}>
                        {meta.label}
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-1.5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: i * 0.06 + 0.15, duration: 0.5, ease: "easeOut" }}
                      className={`h-full rounded-full ${meta.bar}`}
                    />
                  </div>
                  <div className="flex gap-2.5">
                    {account.no_shows > 0 && (
                      <span className="text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">
                        {account.no_shows} no-show{account.no_shows > 1 ? "s" : ""}
                      </span>
                    )}
                    {account.rejections > 0 && (
                      <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                        {account.rejections} rejection{account.rejections > 1 ? "s" : ""}
                      </span>
                    )}
                    {account.aging_critical > 0 && (
                      <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">
                        {account.aging_critical} aging
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
