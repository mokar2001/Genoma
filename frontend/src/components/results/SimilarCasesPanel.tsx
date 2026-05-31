import { motion } from "framer-motion";
import { Users, Dna } from "lucide-react";
import type { SimilarCase } from "@/types/pipeline";

export default function SimilarCasesPanel({ cases }: { cases: SimilarCase[] }) {
  if (!cases || cases.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
        <Users className="mb-3 h-12 w-12 opacity-30" />
        <p className="text-sm">No similar cases found in the reference database</p>
        <p className="text-xs">The case index may still be building (RareBench)</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        Most similar historical cases by phenotype profile (cosine similarity over BioLORD embeddings).
      </p>
      {cases.map((c, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="card p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-900 dark:text-white">{c.disease}</span>
                {c.gene && (
                  <span className="flex items-center gap-1 font-mono text-xs text-indigo-600 dark:text-indigo-400">
                    <Dna className="h-3 w-3" /> {c.gene}
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">{c.source}</span>
                {c.omim_id && <span>OMIM: {c.omim_id}</span>}
                {c.orpha_code && <span>{c.orpha_code}</span>}
                <span>{c.overlap_count} shared HPO terms</span>
              </div>
              {c.hpo_overlap?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {c.hpo_overlap.map((h) => (
                    <span key={h} className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-300">
                      {h}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-lg font-bold text-indigo-600">{(c.score * 100).toFixed(0)}%</div>
              <div className="text-xs text-slate-400">similarity</div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
