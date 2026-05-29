import { motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle, Brain, Microscope, Atom, FileText, Dna } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PipelineStage, StageStatus, SSEEvent } from "@/types/pipeline";

const STAGES: { key: PipelineStage; label: string; icon: React.ElementType; desc: string }[] = [
  { key: "parsing_vcf", label: "VCF Parsing", icon: Dna, desc: "Reading and validating genomic variants" },
  { key: "deeprare", label: "DeepRare", icon: Brain, desc: "Phenotype-genotype disease ranking" },
  { key: "acmg", label: "ACMG Classifier", icon: Microscope, desc: "Variant pathogenicity classification" },
  { key: "alphafold", label: "AlphaFold3", icon: Atom, desc: "3D protein structure prediction" },
  { key: "generating_report", label: "Report", icon: FileText, desc: "Compiling diagnostic evidence" },
];

interface Props {
  events: SSEEvent[];
  overallProgress: number;
}

export default function PipelineStepper({ events, overallProgress }: Props) {
  const stageMap = new Map(events.map((e) => [e.stage, e]));

  const getStatus = (key: PipelineStage): StageStatus => {
    const evt = stageMap.get(key);
    return evt?.status ?? "pending";
  };

  const latestMessage = events[events.length - 1]?.message ?? "Initializing…";

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div>
        <div className="mb-1 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-700 dark:text-slate-300">Pipeline Progress</span>
          <span className="font-semibold text-indigo-600">{overallProgress}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
            initial={{ width: 0 }}
            animate={{ width: `${overallProgress}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">{latestMessage}</p>
      </div>

      {/* Stages */}
      <div className="space-y-3">
        {STAGES.map(({ key, label, icon: Icon, desc }) => {
          const status = getStatus(key);
          const evt = stageMap.get(key);

          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className={cn(
                "flex items-center gap-4 rounded-xl border p-4 transition-all",
                status === "running"
                  ? "border-indigo-200 bg-indigo-50/50 dark:border-indigo-700 dark:bg-indigo-900/20"
                  : status === "complete"
                    ? "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-900/10"
                    : status === "error"
                      ? "border-red-200 bg-red-50/50 dark:border-red-800"
                      : "border-slate-100 bg-white dark:border-slate-800 dark:bg-slate-900"
              )}
            >
              {/* Icon */}
              <div
                className={cn(
                  "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl",
                  status === "running"
                    ? "bg-gradient-to-br from-indigo-500 to-violet-600"
                    : status === "complete"
                      ? "bg-green-500"
                      : status === "error"
                        ? "bg-red-500"
                        : "bg-slate-100 dark:bg-slate-800"
                )}
              >
                {status === "running" ? (
                  <Loader2 className="h-5 w-5 animate-spin text-white" />
                ) : status === "complete" ? (
                  <CheckCircle2 className="h-5 w-5 text-white" />
                ) : status === "error" ? (
                  <XCircle className="h-5 w-5 text-white" />
                ) : (
                  <Icon className="h-5 w-5 text-slate-400" />
                )}
              </div>

              {/* Text */}
              <div className="flex-1 min-w-0">
                <p className={cn(
                  "text-sm font-semibold",
                  status === "running" ? "text-indigo-700 dark:text-indigo-300"
                    : status === "complete" ? "text-green-700 dark:text-green-300"
                    : "text-slate-600 dark:text-slate-400"
                )}>
                  {label}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {status === "running" ? evt?.message : status === "complete" ? evt?.message : desc}
                </p>
              </div>

              {/* Status badge */}
              <StatusBadge status={status} />
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: StageStatus }) {
  if (status === "pending") return <span className="text-xs text-slate-400">Waiting</span>;
  if (status === "running") return (
    <span className="flex items-center gap-1 text-xs font-medium text-indigo-600">
      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" />
      Running
    </span>
  );
  if (status === "complete") return <span className="text-xs font-medium text-green-600">Done</span>;
  return <span className="text-xs font-medium text-red-500">Error</span>;
}
