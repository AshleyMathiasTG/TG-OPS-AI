"use client";
import { motion } from "framer-motion";
import { Users } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { RecruiterStat } from "@/lib/api";

interface RecruiterStatsProps {
  data: RecruiterStat[];
}

const PALETTE = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ec4899"];

export function RecruiterStats({ data }: RecruiterStatsProps) {
  const safeData = data ?? [];
  const maxActive = Math.max(...safeData.map((r) => r.active), 1);

  return (
    <Card className="border-white/10">
      <CardHeader className="pb-3 px-5 pt-5">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-blue-400" />
          <CardTitle className="text-sm font-semibold">Recruiter Load Overview</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="px-5 pb-5">
        {safeData.length === 0 ? (
          <p className="text-center text-gray-600 text-xs py-8">No recruiter data available</p>
        ) : (
          <div className="space-y-4">
            {safeData.map((r, i) => {
              const loadPct = Math.round((r.active / maxActive) * 100);
              const color = PALETTE[i % PALETTE.length];
              const isOverloaded = r.active >= 4 || r.no_shows >= 2;
              return (
                <motion.div
                  key={r.recruiter}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06 }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
                           style={{ background: color + "33", border: `1px solid ${color}44` }}>
                        {r.recruiter.charAt(0)}
                      </div>
                      <span className="text-xs font-medium text-gray-200">{r.recruiter.split(" ")[0]}</span>
                      {isOverloaded && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/20 font-semibold">
                          OVERLOADED
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-bold" style={{ color }}>{r.active} active</span>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-1.5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${loadPct}%` }}
                      transition={{ delay: i * 0.06 + 0.15, duration: 0.5, ease: "easeOut" }}
                      className="h-full rounded-full"
                      style={{ background: color }}
                    />
                  </div>
                  <div className="flex gap-2">
                    {r.no_shows > 0 && (
                      <span className="text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">
                        {r.no_shows} no-show{r.no_shows > 1 ? "s" : ""}
                      </span>
                    )}
                    {r.rejections > 0 && (
                      <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                        {r.rejections} rejection{r.rejections > 1 ? "s" : ""}
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
