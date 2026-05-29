import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { toast } from "sonner";
import {
  Brain, Microscope, Atom, Download, RotateCcw,
  CheckCircle2, Clock, FileText, Share2
} from "lucide-react";
import { usePipelineStore } from "@/store/pipelineStore";
import DeepRarePanel from "@/components/results/DeepRarePanel";
import ACMGPanel from "@/components/results/ACMGPanel";
import AlphaFoldPanel from "@/components/results/AlphaFoldPanel";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "deeprare", label: "DeepRare", icon: Brain, color: "text-indigo-600" },
  { id: "acmg", label: "ACMG Classification", icon: Microscope, color: "text-violet-600" },
  { id: "alphafold", label: "AlphaFold3 Structure", icon: Atom, color: "text-fuchsia-600" },
] as const;

type TabId = typeof TABS[number]["id"];

export default function ResultsPage() {
  const { result, reset } = usePipelineStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>("deeprare");
  const [downloading, setDownloading] = useState(false);

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <p className="text-slate-500">No results yet. Run a diagnostic first.</p>
        <button
          onClick={() => navigate("/diagnose")}
          className="gradient-brand rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
        >
          Start Diagnosis
        </button>
      </div>
    );
  }

  const topDisease = result.deeprare.candidates[0];
  const actionableCount = result.acmg.pathogenic_count + result.acmg.likely_pathogenic_count;

  const handleDownloadPDF = async () => {
    setDownloading(true);
    try {
      const response = await axios.post("/api/report/generate", result, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `raredx-${result.session_id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF report downloaded");
    } catch {
      toast.error("Failed to generate PDF");
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadJSON = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `raredx-${result.session_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("JSON data downloaded");
  };

  const handleNewCase = () => {
    reset();
    navigate("/diagnose");
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6 space-y-4"
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                Diagnostic Results
              </h1>
            </div>
            <p className="text-sm text-slate-500">
              Patient: <span className="font-semibold text-slate-700 dark:text-slate-300">{result.patient_name}</span>
              <span className="mx-2 text-slate-300">·</span>
              Session: <span className="font-mono text-xs">{result.session_id}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleDownloadJSON}
              className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <FileText className="h-3.5 w-3.5" /> JSON
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={downloading}
              className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-60 dark:bg-indigo-900/30 dark:text-indigo-300"
            >
              <Download className="h-3.5 w-3.5" />
              {downloading ? "Generating…" : "PDF Report"}
            </button>
            <button
              onClick={handleNewCase}
              className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <RotateCcw className="h-3.5 w-3.5" /> New Case
            </button>
          </div>
        </div>

        {/* Summary strip */}
        <div
          className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 p-4 text-white"
          dangerouslySetInnerHTML={{ __html: result.summary }}
        />

        {/* Key metrics */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard
            icon={Brain}
            label="Top Diagnosis"
            value={topDisease.disease_name}
            sub={`${(topDisease.score * 100).toFixed(0)}% confidence`}
            color="bg-indigo-50 dark:bg-indigo-900/20"
          />
          <MetricCard
            icon={Microscope}
            label="Actionable Variants"
            value={String(actionableCount)}
            sub={`${result.acmg.vus_count} VUS remaining`}
            color="bg-violet-50 dark:bg-violet-900/20"
          />
          <MetricCard
            icon={Atom}
            label="Structures Analyzed"
            value={String(result.alphafold.length)}
            sub="Wild-type + mutant"
            color="bg-fuchsia-50 dark:bg-fuchsia-900/20"
          />
          <MetricCard
            icon={Clock}
            label="Time Saved"
            value="5–7 years"
            sub="vs. traditional pathway"
            color="bg-green-50 dark:bg-green-900/20"
          />
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border bg-white p-1 dark:bg-slate-900">
        {TABS.map(({ id, label, icon: Icon, color }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
              activeTab === id
                ? "bg-slate-100 shadow-sm dark:bg-slate-800"
                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            )}
          >
            <Icon className={cn("h-4 w-4", activeTab === id ? color : "text-slate-400")} />
            <span className={activeTab === id ? color : ""}>{label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {activeTab === "deeprare" && <DeepRarePanel result={result.deeprare} />}
        {activeTab === "acmg" && <ACMGPanel result={result.acmg} />}
        {activeTab === "alphafold" && <AlphaFoldPanel results={result.alphafold} />}
      </motion.div>

      {/* Evidence chain footer */}
      <div className="card p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">Evidence Chain</p>
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <Chain label="Symptoms" value={`${result.deeprare.phenotype_terms_matched} HPO terms`} />
          <Arrow />
          <Chain label="Disease" value={topDisease.disease_name} highlight />
          <Arrow />
          <Chain label="Variants" value={`${result.acmg.variants.length} classified`} />
          <Arrow />
          <Chain label="Protein" value={`${result.alphafold.length} structure(s)`} />
          <Arrow />
          <Chain label="Verdict" value={`${actionableCount} actionable`} highlight />
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value: string; sub: string; color: string;
}) {
  return (
    <div className={cn("rounded-xl p-3", color)}>
      <Icon className="mb-1.5 h-5 w-5 text-slate-500" />
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-bold text-slate-900 dark:text-white text-sm leading-tight">{value}</p>
      <p className="text-xs text-slate-400">{sub}</p>
    </div>
  );
}

function Chain({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={cn(
      "rounded-lg px-3 py-1.5",
      highlight ? "bg-indigo-100 dark:bg-indigo-900/30" : "bg-slate-50 dark:bg-slate-800"
    )}>
      <span className="text-slate-400">{label}: </span>
      <span className={cn("font-semibold", highlight ? "text-indigo-700 dark:text-indigo-300" : "text-slate-700 dark:text-slate-300")}>
        {value}
      </span>
    </div>
  );
}

function Arrow() {
  return <span className="text-slate-300 dark:text-slate-600">→</span>;
}
