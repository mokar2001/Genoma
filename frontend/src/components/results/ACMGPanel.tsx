import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldAlert, ChevronDown, ChevronUp, ExternalLink, CheckCircle2, XCircle } from "lucide-react";
import { cn, classificationBadge, formatAF } from "@/lib/utils";
import type { ACMGResult, VariantResult, ACMGCriterion } from "@/types/pipeline";

interface Props {
  result: ACMGResult;
}

export default function ACMGPanel({ result }: Props) {
  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Pathogenic" value={result.pathogenic_count} color="text-red-600" />
        <StatCard label="Likely Path." value={result.likely_pathogenic_count} color="text-orange-500" />
        <StatCard label="VUS" value={result.vus_count} color="text-yellow-600" />
        <StatCard label="Benign" value={result.benign_count} color="text-green-600" />
      </div>

      {result.actionable_variants.length > 0 && (
        <div className="flex items-start gap-2 rounded-xl bg-red-50 p-3 dark:bg-red-900/20">
          <ShieldAlert className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
          <div>
            <p className="text-xs font-semibold text-red-700 dark:text-red-300">Actionable Variants Detected</p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
              {result.actionable_variants.join(", ")} — clinical action warranted
            </p>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {result.variants.map((v, i) => (
          <VariantCard key={v.variant_id} variant={v} index={i} />
        ))}
      </div>

      <p className="text-xs text-slate-400">Classification engine: {result.classifier_version}</p>
    </div>
  );
}

function VariantCard({ variant: v, index }: { variant: VariantResult; index: number }) {
  const [expanded, setExpanded] = useState(v.actionable);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className={cn(
        "rounded-xl border",
        v.actionable
          ? "border-red-200 bg-red-50/30 dark:border-red-800 dark:bg-red-900/10"
          : "bg-white dark:bg-slate-900"
      )}
    >
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm font-bold text-slate-900 dark:text-white">{v.gene}</span>
            <span className="font-mono text-xs text-slate-500">{v.cdna_change}</span>
            <span className="font-mono text-xs text-slate-400">{v.protein_change}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={classificationBadge(v.classification)}>{v.classification}</span>
            <span className="text-xs text-slate-400">{v.zygosity}</span>
            <span className="text-xs text-slate-400">chr{v.chromosome}:{v.position.toLocaleString()}</span>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-slate-400">gnomAD AF</p>
          <p className="text-xs font-mono font-medium text-slate-600 dark:text-slate-400">{formatAF(v.gnomad_af)}</p>
        </div>
        {expanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-4 dark:border-slate-700">
          {/* ACMG Criteria */}
          <div>
            <p className="text-xs font-semibold text-slate-500 mb-2">ACMG/AMP Criteria</p>
            <div className="flex flex-wrap gap-2">
              {v.criteria_met.map((c) => (
                <CriterionBadge key={c.code} criterion={c} />
              ))}
            </div>
          </div>

          {/* Criteria details */}
          <div className="space-y-2">
            {v.criteria_met.map((c) => (
              <div key={c.code} className="flex gap-2 text-xs">
                <span className={cn(
                  "mt-0.5 flex-shrink-0 font-bold",
                  c.strength.startsWith("Pathogenic") ? "text-red-500" : "text-green-600"
                )}>
                  {c.code}
                </span>
                <span className="text-slate-600 dark:text-slate-400">{c.description}</span>
              </div>
            ))}
          </div>

          {/* Clinical significance */}
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs text-slate-600 dark:text-slate-400">{v.clinical_significance}</p>
          </div>

          {/* Recommendation */}
          <div className={cn(
            "rounded-lg p-3",
            v.actionable ? "bg-red-50 dark:bg-red-900/20" : "bg-blue-50 dark:bg-blue-900/20"
          )}>
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Clinical Recommendation</p>
            <p className="text-xs text-slate-600 dark:text-slate-400">{v.recommendation}</p>
          </div>

          {/* Diseases */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Associated Diseases</p>
            <div className="flex flex-wrap gap-1">
              {v.associated_diseases.map((d) => (
                <span key={d} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-400">{d}</span>
              ))}
            </div>
          </div>

          {/* ClinVar link */}
          <a
            href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${v.gene}[gene]+AND+${v.cdna_change}`}
            target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-indigo-600 hover:underline"
          >
            Search ClinVar <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}
    </motion.div>
  );
}

function CriterionBadge({ criterion: c }: { criterion: ACMGCriterion }) {
  const isPath = c.strength.startsWith("Pathogenic");
  return (
    <div className={cn(
      "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold",
      isPath
        ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
        : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
    )}>
      {c.met ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {c.code}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border bg-white p-3 text-center dark:bg-slate-900">
      <p className={cn("text-2xl font-bold", color)}>{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}
