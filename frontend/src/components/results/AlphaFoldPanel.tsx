import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Atom, AlertTriangle, ArrowUpCircle, Loader2, RefreshCw, ExternalLink } from "lucide-react";
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
        <StructureCard key={`${r.gene}-${i}`} result={r} index={i} />
      ))}
    </div>
  );
}

type ViewerState = "idle" | "loading" | "loaded" | "error";

function StructureCard({ result: r, index }: { result: AlphaFoldResult; index: number }) {
  const [activeView, setActiveView] = useState<"wt" | "mut">("wt");
  const [viewerState, setViewerState] = useState<ViewerState>("idle");
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerInstanceRef = useRef<any>(null);

  const uniprot = r.wild_type_structure.uniprot_id;
  const pdbUrl = `https://alphafold.ebi.ac.uk/files/AF-${uniprot}-F1-model_v4.pdb`;
  const variantPos = r.wild_type_structure.variant_position;

  const loadStructure = useCallback(async () => {
    if (!containerRef.current) return;

    // Destroy previous viewer cleanly
    if (viewerInstanceRef.current) {
      try {
        viewerInstanceRef.current.clear();
      } catch (_) {}
      viewerInstanceRef.current = null;
    }

    // Clear container completely before 3Dmol touches it
    containerRef.current.innerHTML = "";
    setViewerState("loading");

    try {
      const $3Dmol = (await import("3dmol")).default;

      // Container must have explicit pixel size — 3Dmol ignores CSS %
      const w = containerRef.current.clientWidth || 480;
      const h = 280;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const viewer = $3Dmol.createViewer(containerRef.current, {
        backgroundColor: "0x0f172a",
        antialias: true,
      } as any);

      viewerInstanceRef.current = viewer;

      // Fetch PDB via backend proxy to avoid CORS, fallback to direct
      let pdbText: string | null = null;

      // Try fetching through our backend proxy
      try {
        const proxyResp = await fetch(
          `/api/proxy/pdb?url=${encodeURIComponent(pdbUrl)}`,
          { signal: AbortSignal.timeout(10000) }
        );
        if (proxyResp.ok) pdbText = await proxyResp.text();
      } catch (_) {}

      // Direct fetch as fallback
      if (!pdbText) {
        try {
          const directResp = await fetch(pdbUrl, {
            signal: AbortSignal.timeout(12000),
          });
          if (directResp.ok) pdbText = await directResp.text();
        } catch (_) {}
      }

      if (!pdbText) {
        setViewerState("error");
        return;
      }

      viewer.addModel(pdbText, "pdb");

      // Style: cartoon colored by spectrum (WT) or red (mutant)
      if (activeView === "wt") {
        viewer.setStyle({}, { cartoon: { color: "spectrum" } });
      } else {
        viewer.setStyle({}, { cartoon: { color: "0xef4444", opacity: 0.85 } });
      }

      // Highlight variant position as a sphere
      if (variantPos > 0) {
        viewer.addStyle(
          { resi: variantPos },
          {
            sphere: {
              color: activeView === "wt" ? "0x22c55e" : "0xf97316",
              radius: 1.2,
              opacity: 0.9,
            },
          }
        );

        // Label the variant
        viewer.addLabel(
          `${r.wild_type_structure.wild_type_residue}${variantPos}${activeView === "mut" ? r.wild_type_structure.mutant_residue : ""}`,
          {
            backgroundColor: "0x1e293b",
            fontColor: "white",
            fontSize: 12,
            borderThickness: 1,
            borderColor: "0x6366f1",
          } as any
        );
      }

      viewer.zoomTo();
      viewer.render();
      viewer.zoom(0.9, 800);

      setViewerState("loaded");
    } catch (e) {
      console.error("3Dmol error:", e);
      setViewerState("error");
    }
  }, [activeView, pdbUrl, variantPos]);

  useEffect(() => {
    loadStructure();

    return () => {
      if (viewerInstanceRef.current) {
        try { viewerInstanceRef.current.clear(); } catch (_) {}
        viewerInstanceRef.current = null;
      }
    };
  }, [loadStructure]);

  const handleViewToggle = (view: "wt" | "mut") => {
    if (view !== activeView) setActiveView(view);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-xl border bg-white dark:bg-slate-900 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b px-4 py-3 dark:border-slate-700">
        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-fuchsia-500 to-pink-600">
          <Atom className="h-5 w-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-slate-900 dark:text-white">{r.gene}</span>
            <span className="font-mono text-xs text-slate-400">{r.variant}</span>
            {r.pathogenicity_upgrade && (
              <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                <ArrowUpCircle className="h-3 w-3" />
                Upgraded: {r.upgraded_from} → {r.upgraded_to}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            UniProt: <span className="font-mono">{uniprot}</span> ·
            RMSD: <span className="font-semibold text-slate-700 dark:text-slate-300">{r.rmsd}Å</span> ·
            plDDT WT: <span className="font-semibold">{r.wild_type_structure.plddt_score}</span> →
            Mut: <span className={cn("font-semibold", r.mutant_structure.plddt_score < 70 ? "text-red-500" : "text-orange-500")}>
              {r.mutant_structure.plddt_score}
            </span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5">
        {/* 3D Viewer column */}
        <div className="lg:col-span-3 flex flex-col">
          {/* Controls */}
          <div className="flex items-center justify-between px-4 pt-3 pb-2">
            <div className="flex gap-2">
              <ViewToggle
                active={activeView === "wt"}
                onClick={() => handleViewToggle("wt")}
                label="Wild-Type"
                colorClass="text-green-400"
              />
              <ViewToggle
                active={activeView === "mut"}
                onClick={() => handleViewToggle("mut")}
                label="Mutant"
                colorClass="text-red-400"
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={loadStructure}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Reload structure"
              >
                <RefreshCw className="h-3 w-3" /> Reload
              </button>
              <a
                href={`https://alphafold.ebi.ac.uk/entry/${uniprot}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
              >
                <ExternalLink className="h-3 w-3" /> EBI
              </a>
            </div>
          </div>

          {/* Viewer container — fixed height, relative position */}
          <div className="relative mx-4 mb-4 rounded-xl overflow-hidden bg-slate-950" style={{ height: 280 }}>
            {/* The div 3Dmol renders INTO — must be empty, sized with style */}
            <div
              ref={containerRef}
              style={{ width: "100%", height: "100%", position: "relative" }}
            />

            {/* Loading overlay */}
            {viewerState === "loading" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 z-10">
                <Loader2 className="h-8 w-8 animate-spin text-fuchsia-400 mb-2" />
                <p className="text-xs text-slate-400">Loading {uniprot}…</p>
              </div>
            )}

            {/* Error state */}
            {viewerState === "error" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950 z-10 space-y-3">
                <Atom className="h-10 w-10 text-slate-600" />
                <p className="text-xs text-slate-500">Structure unavailable</p>
                <div className="flex gap-2">
                  <button
                    onClick={loadStructure}
                    className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                  >
                    Retry
                  </button>
                  <a
                    href={pdbUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg bg-indigo-900/40 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-900/60"
                  >
                    Open PDB
                  </a>
                </div>
              </div>
            )}

            {/* Idle (before load) */}
            {viewerState === "idle" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950 z-10">
                <Atom className="h-8 w-8 text-slate-600 animate-pulse" />
              </div>
            )}
          </div>

          {/* Legend */}
          <div className="flex gap-4 px-4 pb-3 text-xs text-slate-500">
            <span>
              <span className="inline-block h-2 w-2 rounded-full bg-green-400 mr-1" />
              Position {variantPos}
            </span>
            <span>
              <span className="inline-block h-2 w-2 rounded-full bg-blue-400 mr-1" />
              Protein chain
            </span>
            {activeView === "mut" && (
              <span>
                <span className="inline-block h-2 w-2 rounded-full bg-orange-400 mr-1" />
                Mutant residue
              </span>
            )}
          </div>
        </div>

        {/* Analysis column */}
        <div className="border-t lg:border-l lg:border-t-0 px-4 py-4 space-y-4 lg:col-span-2 dark:border-slate-700">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
              Structural Impacts
            </p>
            <div className="space-y-2.5">
              {r.structural_impacts.map((impact, i) => (
                <div key={i} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      {impact.impact_type}
                    </span>
                    <span className={cn("text-xs font-bold", severityColor(impact.severity))}>
                      {impact.severity}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{impact.affected_domain}</p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {impact.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg bg-gradient-to-br from-fuchsia-50 to-pink-50 p-3 dark:from-fuchsia-900/10 dark:to-pink-900/10">
            <p className="text-xs font-semibold text-fuchsia-700 dark:text-fuchsia-300 mb-1">
              Functional Summary
            </p>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              {r.functional_summary}
            </p>
          </div>

          <div className="flex items-start gap-2 text-xs text-slate-500">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
            <span>Mutant structure is computationally predicted — not experimentally validated</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ViewToggle({
  active, onClick, label, colorClass,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  colorClass: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-lg px-3 py-1.5 text-xs font-semibold transition-all",
        active
          ? `bg-slate-800 ${colorClass}`
          : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
      )}
    >
      {label}
    </button>
  );
}
