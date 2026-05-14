"use client";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { RefreshCw, ShieldCheck } from "lucide-react";
import { getApprovals, type Approval } from "@/lib/api";
import { ApprovalCard } from "@/components/approvals/ApprovalCard";
import { Button } from "@/components/ui/button";

const statusFilters = ["All", "PENDING", "APPROVED", "REJECTED"];

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  const loadApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getApprovals();
      setApprovals(result ?? []);
    } catch {
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  const filtered = filter === "All" ? approvals : approvals.filter((a) => a.status === filter);
  const pendingCount = approvals.filter((a) => a.status === "PENDING").length;

  return (
    <div className="max-w-3xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <ShieldCheck className="w-5 h-5 text-purple-400" />
            <h2 className="text-xl font-bold text-white">Approval Center</h2>
            {pendingCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 text-xs font-semibold">
                {pendingCount} pending
              </span>
            )}
            {approvals.length > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] text-gray-400 font-medium">
                Last 60 days
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {loading
              ? "Loading…"
              : approvals.length === 0
              ? "No recommendations yet — run the pipeline to generate approvals"
              : "AI-generated recommendations awaiting human review"}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={loadApprovals} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Consecutive issue context — only when there are PENDING items */}
      {pendingCount > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20"
        >
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse shrink-0" />
          <p className="text-xs text-purple-300">
            These recommendations were triggered because the same issue occurred{" "}
            <strong>3+ consecutive times</strong>. AI confidence scores reflect pattern strength.
          </p>
        </motion.div>
      )}

      {/* Status filter — only when there are approvals */}
      {approvals.length > 0 && (
        <div className="flex gap-2">
          {statusFilters.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                filter === f
                  ? "bg-white/15 text-white"
                  : "bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300"
              }`}
            >
              {f}
              {f !== "All" && (
                <span className="ml-1 text-[10px] opacity-60">
                  {approvals.filter((a) => a.status === f).length}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {!loading && approvals.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-white/10 bg-white/2 text-center"
        >
          <ShieldCheck className="w-10 h-10 text-gray-700 mb-3" />
          <p className="text-sm font-medium text-gray-400">No approval requests</p>
          <p className="text-xs text-gray-600 mt-1 max-w-xs">
            Recommendations are generated when the same issue is detected 3+ consecutive times by the AI pipeline.
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {filtered.length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-10">No approvals in this category</p>
          ) : (
            filtered.map((approval) => (
              <ApprovalCard key={approval.id} approval={approval} onUpdate={loadApprovals} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
