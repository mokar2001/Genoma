import { motion } from "framer-motion";
import { Trophy, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { DeepRareResult, DiseaseCandidate } from "@/types/pipeline";

interface Props {
  result: DeepRareResult;
}

export default function DeepRarePanel({ result }: Props) {
  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-3">
        <Metric label="Variants Analyzed" value={result.total_variants_analyzed} />
        <Metric label="HPO Terms Matched" value={result.phenotype_terms_matched} />
        <Metric label="Candidate Diseases" value={result.candidates.length} />
      </div>

      <p className="text-xs text-slate-500 italic">{result.confidence_note}</p>

      {/* Candidates */}
      <div className="space-y-3">
        {result.candidates.map((c, i) => (
          <CandidateCard key={c.orpha_code} candidate={c} primary={i === 0} index={i} />
        ))}
      </div>
    </div>
  );
}

function CandidateCard({ candidate: c, primary, index }: { candidate: DiseaseCandidate; primary: boolean; index: number }) {
  const [expanded, setExpanded] = useState(primary);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={cn(
        "rounded-xl border",
        primary
          ? "border-indigo-200 bg-indigo-50/40 dark:border-indigo-700 dark:bg-indigo-900/10"
          : "bg-white dark:bg-slate-900"
      )}
    >
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        onClick={() => setExpanded((e) => !e)}
      >
        {/* Rank medal */}
        <div className={cn(
          "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold",
          index === 0 ? "bg-amber-400 text-white" : index === 1 ? "bg-slate-300 text-slate-700" : "bg-amber-700/40 text-amber-900 dark:text-amber-300"
        )}>
          {index === 0 ? <Trophy className="h-4 w-4" /> : `#${c.rank}`}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-900 dark:text-white text-sm">{c.disease_name}</span>
            {primary && (
              <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white">
                Top Candidate
              </span>
            )}
          </div>
          <div className="flex gap-3 text-xs text-slate-500 mt-0.5">
            <span>{c.orpha_code}</span>
            {c.omim_id && <span>OMIM: {c.omim_id}</span>}
            <span>{c.inheritance_pattern}</span>
          </div>
        </div>

        {/* Score */}
        <div className="text-right flex-shrink-0">
          <ScoreBar score={c.score} />
        </div>
        {expanded ? <ChevronUp className="h-4 w-4 text-slate-400 flex-shrink-0" /> : <ChevronDown className="h-4 w-4 text-slate-400 flex-shrink-0" />}
      </button>

      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-4 dark:border-slate-700">
          {/* Score breakdown */}
          <div className="grid grid-cols-3 gap-3">
            <ScorePill label="Overall" score={c.score} />
            <ScorePill label="Phenotype" score={c.phenotype_match_score} />
            <ScorePill label="Genotype" score={c.genotype_match_score} />
          </div>

          {/* Info grid */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <InfoRow label="Prevalence" value={c.prevalence} />
            <InfoRow label="Genes" value={c.supporting_genes.join(", ")} />
          </div>

          {/* Symptoms */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-1.5 text-xs font-medium text-green-700 dark:text-green-400">✓ Matched Symptoms</p>
              <div className="flex flex-wrap gap-1">
                {c.matched_symptoms.map((s) => (
                  <span key={s} className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-300">{s}</span>
                ))}
              </div>
            </div>
            {c.unmatched_symptoms.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-medium text-slate-400">✗ Unmatched</p>
                <div className="flex flex-wrap gap-1">
                  {c.unmatched_symptoms.map((s) => (
                    <span key={s} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800">{s}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Reasoning */}
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs font-medium text-slate-500 mb-1">AI Reasoning</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{c.reasoning}</p>
          </div>

          {/* External links */}
          <div className="flex gap-3">
            <a href={`https://www.orpha.net/consor/cgi-bin/OC_Exp.php?Expert=${c.orpha_code.replace("ORPHA:", "")}`}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-indigo-600 hover:underline">
              Orphanet <ExternalLink className="h-3 w-3" />
            </a>
            {c.omim_id && (
              <a href={`https://www.omim.org/entry/${c.omim_id}`} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-indigo-600 hover:underline">
                OMIM <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-500" : "bg-slate-300";
  return (
    <div className="flex flex-col items-end gap-0.5">
      <span className="text-sm font-bold text-slate-900 dark:text-white">{pct}%</span>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ScorePill({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="rounded-lg bg-white p-2 text-center dark:bg-slate-800 border dark:border-slate-700">
      <p className="text-lg font-bold text-indigo-600">{pct}%</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-slate-400">{label}: </span>
      <span className="font-medium text-slate-700 dark:text-slate-300">{value}</span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border bg-white p-3 text-center dark:bg-slate-900">
      <p className="text-2xl font-bold text-indigo-600">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}
