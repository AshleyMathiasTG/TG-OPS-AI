"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { ThumbsUp, ThumbsDown, CheckCircle2, XCircle, AlertTriangle, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { decideApproval, submitFeedback, type Approval } from "@/lib/api";
import { formatRelativeTime, impactColor } from "@/lib/utils";

interface ApprovalCardProps {
  approval: Approval;
  onUpdate: () => void;
}

const impactVariant: Record<string, "critical" | "warning" | "info" | "success"> = {
  CRITICAL: "critical",
  HIGH: "warning",
  MEDIUM: "info",
  LOW: "success",
};

export function ApprovalCard({ approval, onUpdate }: ApprovalCardProps) {
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [decided, setDecided] = useState(approval.status !== "PENDING");

  const handleDecide = async (status: "APPROVED" | "REJECTED") => {
    setLoading(status === "APPROVED" ? "approve" : "reject");
    try {
      await decideApproval(approval.id, status);
      setDecided(true);
      onUpdate();
    } finally {
      setLoading(null);
    }
  };

  const handleFeedback = async (sentiment: "THUMBS_UP" | "THUMBS_DOWN") => {
    await submitFeedback(approval.id, sentiment);
    setFeedback(sentiment === "THUMBS_UP" ? "up" : "down");
  };

  const confidencePct = Math.round((approval.confidence_score ?? 0) * 100);
  const steps = approval.mitigation_steps?.split("|").map((s) => s.trim()) ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <Card className={`border ${
        approval.status === "APPROVED"
          ? "border-emerald-500/30 bg-emerald-500/5"
          : approval.status === "REJECTED"
          ? "border-red-500/20 bg-red-500/5 opacity-70"
          : "border-white/10"
      }`}>
        <CardContent className="p-5">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <Badge variant={impactVariant[approval.impact_level ?? "MEDIUM"] ?? "info"}>
                  {approval.impact_level ?? "MEDIUM"}
                </Badge>
                <span className="text-xs text-gray-500">{formatRelativeTime(approval.created_at)}</span>
              </div>
              <p className="text-sm font-semibold text-white leading-snug">{approval.issue_summary}</p>
            </div>
            {/* Confidence score */}
            <div className="shrink-0 text-center">
              <div className="relative w-12 h-12">
                <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="2.5" />
                  <circle
                    cx="18" cy="18" r="15.9" fill="none"
                    stroke={confidencePct >= 80 ? "#10b981" : confidencePct >= 60 ? "#f59e0b" : "#ef4444"}
                    strokeWidth="2.5"
                    strokeDasharray={`${confidencePct} ${100 - confidencePct}`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">
                  {confidencePct}%
                </span>
              </div>
              <p className="text-[9px] text-gray-500 mt-0.5">confidence</p>
            </div>
          </div>

          {/* Recommendation */}
          <div className="bg-white/5 rounded-xl p-3 mb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Zap className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-xs font-medium text-purple-300">AI Recommendation</span>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">{approval.recommended_action}</p>
          </div>

          {/* Mitigation steps */}
          {steps.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-400 mb-1.5">Mitigation Steps</p>
              <div className="space-y-1">
                {steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-gray-400">
                    <span className="shrink-0 w-4 h-4 rounded-full bg-white/10 text-gray-300 flex items-center justify-center text-[10px] font-semibold mt-0.5">
                      {i + 1}
                    </span>
                    {step.replace(/^\d+\.\s*/, "")}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Escalation path */}
          {approval.escalation_path && (
            <p className="text-xs text-gray-500 mb-4">
              <span className="text-gray-400">Escalation:</span> {approval.escalation_path}
            </p>
          )}

          {/* Actions */}
          {approval.status === "PENDING" && !decided ? (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="success"
                onClick={() => handleDecide("APPROVED")}
                disabled={loading !== null}
                className="flex-1"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                {loading === "approve" ? "Approving…" : "Approve"}
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => handleDecide("REJECTED")}
                disabled={loading !== null}
                className="flex-1"
              >
                <XCircle className="w-3.5 h-3.5" />
                {loading === "reject" ? "Rejecting…" : "Reject"}
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {approval.status === "APPROVED" || decided ? (
                  <span className="text-xs text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Approved
                  </span>
                ) : (
                  <span className="text-xs text-red-400 flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5" /> Rejected
                  </span>
                )}
              </div>
              {/* Feedback */}
              {!feedback ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Was this helpful?</span>
                  <button onClick={() => handleFeedback("THUMBS_UP")} className="hover:text-emerald-400 text-gray-500 transition-colors">
                    <ThumbsUp className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => handleFeedback("THUMBS_DOWN")} className="hover:text-red-400 text-gray-500 transition-colors">
                    <ThumbsDown className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <span className="text-xs text-gray-500">
                  {feedback === "up" ? "👍 Thanks!" : "👎 Feedback noted"}
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
