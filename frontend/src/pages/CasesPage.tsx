import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { format } from "date-fns";
import {
  Plus,
  Trash2,
  Eye,
  Dna,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface CaseSummary {
  id: string;
  title: string;
  status: "draft" | "running" | "complete" | "failed";
  created_at: string;
  completed_at: string | null;
  patient_name: string | null;
  top_diagnosis: string | null;
  vcf_filename: string | null;
}

const STATUS_CONFIG = {
  draft: {
    icon: FileText,
    color: "text-slate-400",
    bg: "bg-slate-100 dark:bg-slate-800",
    label: "Draft",
    spin: false,
  },
  running: {
    icon: Loader2,
    color: "text-blue-500",
    bg: "bg-blue-50 dark:bg-blue-900/20",
    label: "Running",
    spin: true,
  },
  complete: {
    icon: CheckCircle2,
    color: "text-green-500",
    bg: "bg-green-50 dark:bg-green-900/20",
    label: "Complete",
    spin: false,
  },
  failed: {
    icon: AlertCircle,
    color: "text-red-500",
    bg: "bg-red-50 dark:bg-red-900/20",
    label: "Failed",
    spin: false,
  },
} as const;

export default function CasesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: cases = [], isLoading } = useQuery<CaseSummary[]>({
    queryKey: ["cases"],
    queryFn: () => axios.get("/api/cases").then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => axios.delete(`/api/cases/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      toast.success("Case deleted");
    },
    onError: () => toast.error("Failed to delete case"),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Case History</h1>
          <p className="text-sm text-slate-500">
            {cases.length} case{cases.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          to="/diagnose"
          className="gradient-brand flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25"
        >
          <Plus className="h-4 w-4" /> New Case
        </Link>
      </div>

      {cases.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-24 text-center space-y-4">
          <Dna className="h-16 w-16 text-slate-200 dark:text-slate-700" />
          <p className="text-slate-500">No cases yet</p>
          <Link
            to="/diagnose"
            className="gradient-brand rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
          >
            Create first case
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map((c, i) => {
            const cfg = STATUS_CONFIG[c.status] ?? STATUS_CONFIG.draft;
            const Icon = cfg.icon;
            return (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="card flex items-center gap-4 p-4 hover:shadow-md transition-shadow"
              >
                {/* Status icon */}
                <div
                  className={cn(
                    "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl",
                    cfg.bg
                  )}
                >
                  <Icon
                    className={cn("h-5 w-5", cfg.color, cfg.spin && "animate-spin")}
                  />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-slate-900 dark:text-white truncate">
                      {c.title}
                    </p>
                    <span
                      className={cn(
                        "text-xs font-medium px-2 py-0.5 rounded-full",
                        cfg.bg,
                        cfg.color
                      )}
                    >
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5 flex-wrap">
                    {c.patient_name && <span>{c.patient_name}</span>}
                    {c.top_diagnosis && (
                      <span className="font-medium text-indigo-600 dark:text-indigo-400 truncate">
                        → {c.top_diagnosis}
                      </span>
                    )}
                    {c.vcf_filename && (
                      <span className="font-mono truncate">VCF: {c.vcf_filename}</span>
                    )}
                  </div>
                </div>

                {/* Date */}
                <div className="text-right flex-shrink-0 text-xs text-slate-400">
                  <p>{format(new Date(c.created_at), "MMM d, yyyy")}</p>
                  <p>{format(new Date(c.created_at), "HH:mm")}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  {c.status === "complete" && (
                    <button
                      onClick={() => navigate(`/results?case=${c.id}`)}
                      className="rounded-lg p-2 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                      title="View results"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => deleteMutation.mutate(c.id)}
                    disabled={deleteMutation.isPending}
                    className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 disabled:opacity-50"
                    title="Delete case"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
