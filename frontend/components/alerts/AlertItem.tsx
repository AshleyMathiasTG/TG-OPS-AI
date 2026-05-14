"use client";
import { motion } from "framer-motion";
import { X, AlertTriangle, AlertCircle, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { dismissAlert, type Alert } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

interface AlertItemProps {
  alert: Alert;
  index: number;
  onDismiss: (id: string) => void;
}

const severityIcon = {
  CRITICAL: AlertTriangle,
  WARNING: AlertCircle,
  INFO: Info,
};

const severityStyles = {
  CRITICAL: "border-red-500/20 bg-red-500/5 hover:bg-red-500/10",
  WARNING: "border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10",
  INFO: "border-blue-500/20 bg-blue-500/5 hover:bg-blue-500/10",
};

const badgeVariant: Record<string, any> = {
  CRITICAL: "critical",
  WARNING: "warning",
  INFO: "info",
};

export function AlertItem({ alert, index, onDismiss }: AlertItemProps) {
  const Icon = severityIcon[alert.severity] ?? Info;
  const style = severityStyles[alert.severity] ?? severityStyles.INFO;

  const handleDismiss = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await dismissAlert(alert.id).catch(() => {});
    onDismiss(alert.id);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      transition={{ delay: index * 0.04 }}
      className={`flex items-start gap-3 p-3 rounded-xl border transition-colors cursor-default ${style}`}
    >
      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${
        alert.severity === "CRITICAL" ? "text-red-400" :
        alert.severity === "WARNING" ? "text-amber-400" : "text-blue-400"
      }`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <Badge variant={badgeVariant[alert.severity]} className="text-[9px] px-1.5 py-0">
            {alert.severity}
          </Badge>
          {alert.entity_name && (
            <span className="text-[10px] text-gray-500">{alert.entity_name}</span>
          )}
          <span className="text-[10px] text-gray-600 ml-auto">{formatRelativeTime(alert.created_at)}</span>
        </div>
        <p className={`text-xs font-medium ${!alert.is_read ? "text-white" : "text-gray-400"}`}>
          {alert.title}
        </p>
        {alert.summary && (
          <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{alert.summary}</p>
        )}
      </div>
      <Button variant="ghost" size="icon" onClick={handleDismiss} className="h-6 w-6 shrink-0 opacity-50 hover:opacity-100">
        <X className="w-3 h-3" />
      </Button>
    </motion.div>
  );
}
