import { motion } from "framer-motion";
import { BookOpen, ExternalLink, Quote } from "lucide-react";
import type { LiteratureItem } from "@/types/pipeline";

export default function LiteraturePanel({ items }: { items: LiteratureItem[] }) {
  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
        <BookOpen className="mb-3 h-12 w-12 opacity-30" />
        <p className="text-sm">No literature retrieved</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        Live retrieval from PubMed / Europe PMC by phenotype + gene keywords.
      </p>
      {items.map((a, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="card p-4"
        >
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-600">
              <Quote className="h-4 w-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-slate-900 hover:text-indigo-600 dark:text-white dark:hover:text-indigo-400"
              >
                {a.title}
              </a>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500 flex-wrap">
                {a.journal && <span className="italic">{a.journal}</span>}
                {a.year && <span>{a.year}</span>}
                {a.citations > 0 && <span>· {a.citations} citations</span>}
                {a.pmid && <span>· PMID {a.pmid}</span>}
              </div>
              {a.snippet && (
                <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-400 line-clamp-3">{a.snippet}</p>
              )}
              {a.url && (
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1.5 inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
                >
                  Read <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
