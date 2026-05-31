import { motion } from "framer-motion";
import {
  CheckCircle2, Loader2, XCircle, Dna, Brain, Users,
  BookOpen, ListFilter, Atom, Stethoscope, FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { PipelineStage, StageStatus, SSEEvent } from "@/types/pipeline";

const STAGES: { key: PipelineStage; label: string; icon: React.ElementType; desc: string }[] = [
  { key: "sequencing", label: "Sequencing", icon: FlaskConical, desc: "nf-core/sarek FASTQ → VCF" },
  { key: "parsing_vcf", label: "VCF Parsing", icon: Dna, desc: "Reading & annotating variants" },
  { key: "phenotype", label: "Phenotyping", icon: Brain, desc: "Text → HPO terms (BioLORD)" },
  { key: "similarity", label: "Similar Cases", icon: Users, desc: "Qdrant case retrieval" },
  { key: "literature", label: "Literature", icon: BookOpen, desc: "PubMed / Europe PMC crawl" },
  { key: "prioritization", label: "Variant Ranking", icon: ListFilter, desc: "AlphaMissense + gnomAD + ClinVar" },
  { key: "structure", label: "Structure", icon: Atom, desc: "AlphaFold molecular impact" },
  { key: "diagnosis", label: "Diagnosis", icon: Stethoscope, desc: "Ranked differential" },
];

const ORDER = STAGES.map((s) => s.key);

interface Props {
  events: SSEEvent[];
  overallProgress: number;
}

export default function PipelineStepper({ events, overallProgress }: Props) {
  const stageMap = new Map(events.map((e) => [e.stage, e]));
  const latest = events[events.length - 1];
  const latestIdx = latest ? ORDER.indexOf(latest.stage) : -1;

  const getStatus = (key: PipelineStage, idx: number): StageStatus => {
    const evt = stageMap.get(key);
    if (evt) return evt.status;
    // Infer: stages before the latest are complete
    if (latest?.stage === "complete") return "complete";
    if (latestIdx >= 0 && idx < latestIdx) return "complete";
    return "pending";
  };

  return (
    <div className="space-y-5">
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
        <p className="mt-2 text-xs text-slate-500">{latest?.message ?? "Initializing…"}</p>
      </div>

      <div className="space-y-2">
        {STAGES.map(({ key, label, icon: Icon, desc }, idx) => {
          const status = getStatus(key, idx);
          const evt = stageMap.get(key);
          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className={cn(
                "flex items-center gap-3 rounded-xl border p-3 transition-all",
                status === "running"
                  ? "border-indigo-200 bg-indigo-50/50 dark:border-indigo-700 dark:bg-indigo-900/20"
                  : status === "complete"
                    ? "border-green-200 bg-green-50/40 dark:border-green-800 dark:bg-green-900/10"
                    : status === "error"
                      ? "border-red-200 bg-red-50/50 dark:border-red-800"
                      : "border-slate-100 bg-white dark:border-slate-800 dark:bg-slate-900"
              )}
            >
              <div className={cn(
                "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg",
                status === "running" ? "bg-gradient-to-br from-indigo-500 to-violet-600"
                  : status === "complete" ? "bg-green-500"
                  : status === "error" ? "bg-red-500"
                  : "bg-slate-100 dark:bg-slate-800"
              )}>
                {status === "running" ? <Loader2 className="h-4 w-4 animate-spin text-white" />
                  : status === "complete" ? <CheckCircle2 className="h-4 w-4 text-white" />
                  : status === "error" ? <XCircle className="h-4 w-4 text-white" />
                  : <Icon className="h-4 w-4 text-slate-400" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className={cn("text-sm font-semibold",
                  status === "running" ? "text-indigo-700 dark:text-indigo-300"
                    : status === "complete" ? "text-green-700 dark:text-green-300"
                    : "text-slate-600 dark:text-slate-400")}>
                  {label}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {(status === "running" || status === "complete") && evt?.message ? evt.message : desc}
                </p>
              </div>
              {status === "running" && (
                <span className="flex items-center gap-1 text-xs font-medium text-indigo-600">
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" />
                </span>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
