"use client";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { BarChart3, RefreshCw } from "lucide-react";
import { getAnalyticsOverview, type AnalyticsData } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { Button } from "@/components/ui/button";

const PIE_COLORS = ["#ef4444", "#8b5cf6", "#f59e0b", "#3b82f6", "#10b981", "#ec4899"];

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-gray-900 border border-white/10 rounded-xl p-2.5 text-xs shadow-xl">
        <p className="text-white font-medium">{payload[0].name}</p>
        <p className="text-gray-300">{payload[0].value}</p>
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAnalyticsOverview();
      // Only set if there's real content
      const hasContent =
        (result?.top_issues?.length ?? 0) > 0 ||
        (result?.risk_by_account?.length ?? 0) > 0 ||
        (result?.recruiter_performance?.length ?? 0) > 0;
      setData(hasContent ? result : null);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pieData = Object.entries(data?.status_distribution ?? {})
    .filter(([, v]) => (v as number) > 0)
    .map(([name, value]) => ({ name, value: value as number }));

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-xl font-bold text-white">Analytics & Insights</h2>
            {data && (
              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-[10px] text-blue-400 font-medium">
                Last 60 days
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {loading ? "Loading…" : "Operational metrics, trend patterns, and recruiter performance"}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={load} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Empty state */}
      {!loading && !data && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-white/10 bg-white/2 text-center"
        >
          <BarChart3 className="w-10 h-10 text-gray-700 mb-3" />
          <p className="text-sm font-medium text-gray-400">No analytics data yet</p>
          <p className="text-xs text-gray-600 mt-1">
            Run the pipeline to generate metrics, trends, and insights.
          </p>
        </motion.div>
      )}

      {/* Data */}
      {!loading && data && (
        <>
          {/* Top issues */}
          {data.top_issues.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {data.top_issues.map((issue, i) => (
                <motion.div
                  key={issue.type}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.06 }}
                  className={`rounded-xl border p-4 ${
                    issue.trend === "up"
                      ? "border-red-500/20 bg-red-500/5"
                      : issue.trend === "down"
                      ? "border-emerald-500/20 bg-emerald-500/5"
                      : "border-white/10 bg-white/3"
                  }`}
                >
                  <p className="text-[11px] text-gray-400 mb-1.5 font-medium">{issue.type}</p>
                  <p className="text-2xl font-bold text-white tabular-nums">{issue.count}</p>
                  <p className={`text-[11px] mt-1.5 font-medium ${
                    issue.trend === "up" ? "text-red-400" : issue.trend === "down" ? "text-emerald-400" : "text-gray-500"
                  }`}>
                    {issue.trend === "up" ? "↑ Increasing" : issue.trend === "down" ? "↓ Improving" : "→ Stable"}
                  </p>
                </motion.div>
              ))}
            </div>
          )}

          {/* Charts */}
          {(pieData.length > 0 || data.risk_by_account.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {pieData.length > 0 && (
                <Card className="border-white/10">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Submission Status Mix</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie data={pieData} cx="50%" cy="50%" innerRadius={48} outerRadius={72} paddingAngle={3} dataKey="value">
                          {pieData.map((_, i) => (
                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} opacity={0.85} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="grid grid-cols-1 gap-1 mt-2">
                      {pieData.map((d, i) => (
                        <div key={d.name} className="flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-1.5 text-gray-400">
                            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                            {d.name}
                          </div>
                          <span className="text-white font-semibold">{d.value}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {data.risk_by_account.length > 0 && (
                <Card className={`border-white/10 ${pieData.length > 0 ? "lg:col-span-2" : "lg:col-span-3"}`}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Account Risk Scores</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={data.risk_by_account} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="account" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="score" name="Risk Score" radius={[4, 4, 0, 0]}>
                          {data.risk_by_account.map((d, i) => (
                            <Cell
                              key={i}
                              fill={d.score >= 10 ? "#ef4444" : d.score >= 6 ? "#f97316" : d.score >= 3 ? "#f59e0b" : "#10b981"}
                              opacity={0.85}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Trend */}
          {(data.trend?.weeks?.length ?? 0) > 1 && <TrendChart data={data.trend} />}

          {/* Recruiter performance */}
          {data.recruiter_performance.length > 0 && (
            <Card className="border-white/10">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Recruiter Performance Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {data.recruiter_performance.map((r, i) => (
                    <motion.div
                      key={r.recruiter}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.07 }}
                      className="rounded-xl border border-white/8 bg-white/3 p-4"
                    >
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-xs font-bold text-gray-200">
                          {r.recruiter.charAt(0)}
                        </div>
                        <p className="text-xs font-semibold text-white truncate">{r.recruiter.split(" ")[0]}</p>
                      </div>
                      <div className="h-1.5 bg-white/8 rounded-full mb-1.5">
                        <div
                          className={`h-full rounded-full transition-all ${
                            r.load_score >= 75 ? "bg-red-500" : r.load_score >= 50 ? "bg-amber-500" : "bg-emerald-500"
                          }`}
                          style={{ width: `${r.load_score}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-gray-500 mb-2">Load: {r.load_score}%</p>
                      <div className="space-y-1 text-[11px]">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Active</span>
                          <span className="text-white font-semibold">{r.active}</span>
                        </div>
                        {r.no_shows > 0 && (
                          <div className="flex justify-between">
                            <span className="text-rose-400">No-shows</span>
                            <span className="text-rose-400 font-semibold">{r.no_shows}</span>
                          </div>
                        )}
                        {r.rejections > 0 && (
                          <div className="flex justify-between">
                            <span className="text-amber-400">Rejections</span>
                            <span className="text-amber-400 font-semibold">{r.rejections}</span>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
