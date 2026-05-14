"use client";
import { motion } from "framer-motion";
import { Sparkles, ChevronRight } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface ExecutiveSummaryProps {
  summary: string;
  highlights: string[];
  generatedAt: string;
}

const highlightColors = [
  "border-l-red-500 bg-red-500/5",
  "border-l-amber-500 bg-amber-500/5",
  "border-l-orange-500 bg-orange-500/5",
  "border-l-purple-500 bg-purple-500/5",
  "border-l-blue-500 bg-blue-500/5",
  "border-l-cyan-500 bg-cyan-500/5",
  "border-l-pink-500 bg-pink-500/5",
  "border-l-emerald-500 bg-emerald-500/5",
];

export function ExecutiveSummary({ summary, highlights, generatedAt }: ExecutiveSummaryProps) {
  return (
    <Card className="border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20">
              <Sparkles className="w-4 h-4 text-purple-400" />
            </div>
            <CardTitle className="text-base">AI Executive Summary</CardTitle>
          </div>
          <span className="text-xs text-gray-500" suppressHydrationWarning>
            {new Date(generatedAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-300 mb-4 leading-relaxed">{summary}</p>
        <div className="space-y-2">
          {highlights.map((highlight, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className={`flex items-start gap-2 pl-3 py-2 rounded-lg border-l-2 ${highlightColors[i % highlightColors.length]}`}
            >
              <ChevronRight className="w-3.5 h-3.5 mt-0.5 text-gray-500 shrink-0" />
              <span className="text-xs text-gray-300">{highlight}</span>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
