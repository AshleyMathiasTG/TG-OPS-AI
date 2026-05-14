"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { TrendData } from "@/lib/api";

interface TrendChartProps {
  data: TrendData;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-900 border border-white/10 rounded-xl p-3 shadow-xl text-xs">
        <p className="text-gray-400 mb-1.5 font-medium">{label}</p>
        {payload.map((entry: any) => (
          <div key={entry.name} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
            <span className="text-gray-300">{entry.name}:</span>
            <span className="text-white font-semibold">{entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export function TrendChart({ data }: TrendChartProps) {
  const chartData = data.weeks.map((week, i) => ({
    week,
    "SLA Breaches": data.sla_breaches[i],
    "No-Shows": data.no_shows[i],
    "Tech Rejections": data.tech_rejections[i],
    "Open Positions": data.open_positions[i],
  }));

  return (
    <Card className="border-white/10">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Operational Trend — 5 Week View</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="week" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#9ca3af", paddingTop: 8 }}
              iconType="circle"
            />
            <Line type="monotone" dataKey="SLA Breaches" stroke="#ef4444" strokeWidth={2} dot={{ r: 3, fill: "#ef4444" }} />
            <Line type="monotone" dataKey="No-Shows" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3, fill: "#f59e0b" }} />
            <Line type="monotone" dataKey="Tech Rejections" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3, fill: "#8b5cf6" }} />
            <Line type="monotone" dataKey="Open Positions" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: "#3b82f6" }} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
