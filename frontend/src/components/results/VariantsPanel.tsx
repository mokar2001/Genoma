import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, ChevronUp, AlertTriangle, Sparkles, ExternalLink } from "lucide-react";
import { cn, formatAF } from "@/lib/utils";
import type { PrioritizedVariant } from "@/types/pipeline";

export default function VariantsPanel({ variants }: { variants: PrioritizedVariant[] }) {
  if (!variants || variants.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
        <AlertTriangle className="mb-3 h-12 w-12 opacity-30" />
        <p className="text-sm">No variants to prioritize</p>
      </div>
    );
  }

  const novelCount = variants.filter((v) => v.novel).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">
          {variants.length} ranked
        </span>
        {novelCount > 0 && (
          <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
            <Sparkles className="h-3 w-3" /> {novelCount} novel
          </span>
        )}
        <span className="text-slate-400">Scored by AlphaMissense + gnomAD + ClinVar + phenotype match</span>
      </div>

      {variants.map((v, i) => (
        <VariantRow key={i} variant={v} index={i} />
      ))}
    </div>
  );
}

function VariantRow({ variant: v, index }: { variant: PrioritizedVariant; index: number }) {
  const [open, setOpen] = useState(index === 0 || v.novel);
  const pct = Math.round(v.priority_score * 100);
  const scoreColor = pct >= 70 ? "text-red-600" : pct >= 40 ? "text-orange-500" : "text-slate-400";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className={cn("rounded-xl border", v.novel
        ? "border-amber-200 bg-amber-50/30 dark:border-amber-800 dark:bg-amber-900/10"
        : "bg-white dark:bg-slate-900")}
    >
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-4 py-3 text-left">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm font-bold text-slate-900 dark:text-white">{v.gene}</span>
            <span className="font-mono text-xs text-slate-500">{v.cdna_change}</span>
            <span className="font-mono text-xs text-slate-400">{v.protein_change}</span>
            {v.novel && (
              <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                <Sparkles className="h-3 w-3" /> Novel
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-slate-400 flex-wrap">
            <span>{v.consequence}</span>
            <span>· {v.zygosity}</span>
            <span>· gnomAD {formatAF(v.gnomad_af)}</span>
            {v.alphamissense && <span>· AM: {v.alphamissense.am_class} ({v.alphamissense.am_pathogenicity.toFixed(2)})</span>}
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <div className={cn("text-lg font-bold", scoreColor)}>{pct}</div>
          <div className="text-xs text-slate-400">priority</div>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {open && (
        <div className="border-t px-4 pb-4 pt-3 space-y-3 dark:border-slate-700">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Info label="ClinVar" value={v.clinvar_significance} />
            <Info label="Consequence" value={v.consequence} />
            <Info label="gnomAD AF" value={formatAF(v.gnomad_af)} />
            {v.franklin && <Info label="Franklin" value={v.franklin} />}
            {v.alphamissense && <Info label="AlphaMissense" value={`${v.alphamissense.am_class} (${v.alphamissense.am_pathogenicity.toFixed(3)})`} />}
            <Info label="Position" value={`chr${v.chromosome}:${v.position?.toLocaleString?.() ?? v.position}`} />
          </div>

          {v.priority_reasons?.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold text-slate-500">Scoring rationale</p>
              <div className="flex flex-wrap gap-1.5">
                {v.priority_reasons.map((r, i) => (
                  <span key={i} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {v.novel && (
            <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-2.5 dark:bg-amber-900/20">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-amber-500" />
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Novel variant — absent from ClinVar and rare in gnomAD. Sent to AlphaFold for structural confirmation (see Structure tab).
              </p>
            </div>
          )}

          <a
            href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${v.gene}[gene]+${v.cdna_change}`}
            target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
          >
            Search ClinVar <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}
    </motion.div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-slate-400">{label}: </span>
      <span className="font-medium text-slate-700 dark:text-slate-300">{value}</span>
    </div>
  );
}
