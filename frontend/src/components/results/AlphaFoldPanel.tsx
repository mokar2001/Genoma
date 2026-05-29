import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Atom, AlertTriangle, ArrowUpCircle } from "lucide-react";
import { cn, severityColor } from "@/lib/utils";
import type { AlphaFoldResult } from "@/types/pipeline";

interface Props {
  results: AlphaFoldResult[];
}

export default function AlphaFoldPanel({ results }: Props) {
  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
        <Atom className="mb-3 h-12 w-12 opacity-30" />
        <p className="text-sm">No actionable variants for structural analysis</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {results.map((r, i) => (
        <StructureCard key={r.gene} result={r} index={i} />
      ))}
    </div>
  );
}

function StructureCard({ result: r, index }: { result: AlphaFoldResult; index: number }) {
  const [activeView, setActiveView] = useState<"wt" | "mut">("wt");
  const viewerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 3Dmol.js viewer integration
    // Phase 2: load actual PDB data from r.pdb_wild_type / r.pdb_mutant
    const load3Dmol = async () => {
      if (!viewerRef.current) return;
      try {
        const $3Dmol = (await import("3dmol")).default;
        const viewer = $3Dmol.createViewer(viewerRef.current, {
          backgroundColor: "0x0f172a",
        });

        // Load structure from URL (EBI AlphaFold)
        const url = activeView === "wt" ? r.wild_type_structure.structure_url : r.mutant_structure.structure_url;

        viewer.addModel("", "pdb"); // placeholder

        // Try to fetch PDB
        const res = await fetch(url).catch(() => null);
        if (res?.ok) {
          const pdbText = await res.text();
          viewer.clear();
          viewer.addModel(pdbText, "pdb");
        }

        viewer.setStyle({}, { cartoon: { color: activeView === "wt" ? "spectrum" : "0xff6b6b" } });

        // Highlight variant position
        const pos = r.wild_type_structure.variant_position;
        viewer.addStyle(
          { resi: pos },
          { sphere: { color: activeView === "wt" ? "0x00ff88" : "0xff3333", radius: 0.8 } }
        );

        viewer.zoomTo();
        viewer.render();
        viewer.zoom(1.2, 500);
      } catch (e) {
        // 3Dmol unavailable — show placeholder
      }
    };

    load3Dmol();
  }, [activeView, r]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-xl border bg-white dark:bg-slate-900 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b px-4 py-3 dark:border-slate-700">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-fuchsia-500 to-pink-600">
          <Atom className="h-5 w-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-900 dark:text-white">{r.gene}</span>
            <span className="font-mono text-xs text-slate-400">{r.variant}</span>
            {r.pathogenicity_upgrade && (
              <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                <ArrowUpCircle className="h-3 w-3" />
                Upgraded: {r.upgraded_from} → {r.upgraded_to}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            RMSD: <span className="font-semibold text-slate-700 dark:text-slate-300">{r.rmsd}Å</span> ·
            plDDT WT: <span className="font-semibold">{r.wild_type_structure.plddt_score}</span> ·
            plDDT Mut: <span className={cn("font-semibold", r.mutant_structure.plddt_score < 70 ? "text-red-500" : "text-orange-500")}>
              {r.mutant_structure.plddt_score}
            </span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-0 lg:grid-cols-5">
        {/* 3D Viewer */}
        <div className="lg:col-span-3">
          <div className="flex gap-2 px-4 pt-3">
            <ViewToggle active={activeView === "wt"} onClick={() => setActiveView("wt")} label="Wild-Type" color="text-green-500" />
            <ViewToggle active={activeView === "mut"} onClick={() => setActiveView("mut")} label="Mutant" color="text-red-500" />
          </div>
          <div
            ref={viewerRef}
            className="mx-4 mb-4 mt-2 h-64 overflow-hidden rounded-xl bg-slate-950 flex items-center justify-center"
          >
            <div className="text-center text-slate-600">
              <Atom className="mx-auto mb-2 h-8 w-8 animate-pulse" />
              <p className="text-xs">Loading structure…</p>
              <p className="text-xs opacity-50">
                {activeView === "wt" ? r.wild_type_structure.uniprot_id : r.mutant_structure.uniprot_id}
              </p>
            </div>
          </div>
          <div className="flex gap-4 px-4 pb-3 text-xs text-slate-500">
            <span><span className="inline-block h-2 w-2 rounded-full bg-green-400 mr-1" />Variant position {r.wild_type_structure.variant_position}</span>
            <span><span className="inline-block h-2 w-2 rounded-full bg-blue-400 mr-1" />Protein chain</span>
          </div>
        </div>

        {/* Analysis */}
        <div className="border-t lg:border-l lg:border-t-0 px-4 py-4 space-y-4 lg:col-span-2 dark:border-slate-700">
          <div>
            <p className="text-xs font-semibold text-slate-500 mb-2">Structural Impacts</p>
            <div className="space-y-3">
              {r.structural_impacts.map((impact, i) => (
                <div key={i} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{impact.impact_type}</span>
                    <span className={cn("text-xs font-bold", severityColor(impact.severity))}>{impact.severity}</span>
                  </div>
                  <p className="text-xs text-slate-500 mb-1">{impact.affected_domain}</p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{impact.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg bg-gradient-to-br from-fuchsia-50 to-pink-50 p-3 dark:from-fuchsia-900/10 dark:to-pink-900/10">
            <p className="text-xs font-semibold text-fuchsia-700 dark:text-fuchsia-300 mb-1">Functional Summary</p>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{r.functional_summary}</p>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            Mutant structure predicted — not experimentally validated
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ViewToggle({ active, onClick, label, color }: {
  active: boolean; onClick: () => void; label: string; color: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-lg px-3 py-1.5 text-xs font-semibold transition-all",
        active
          ? `bg-slate-900 ${color} dark:bg-slate-700`
          : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
      )}
    >
      {label}
    </button>
  );
}
