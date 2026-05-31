import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import axios from "axios";
import { toast } from "sonner";
import {
  Stethoscope, ListFilter, Atom, Users, BookOpen, Brain,
  Download, RotateCcw, CheckCircle2, Clock, Loader2, FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import DeepRarePanel from "@/components/results/DeepRarePanel";
import ACMGPanel from "@/components/results/ACMGPanel";
import AlphaFoldPanel from "@/components/results/AlphaFoldPanel";
import VariantsPanel from "@/components/results/VariantsPanel";
import SimilarCasesPanel from "@/components/results/SimilarCasesPanel";
import LiteraturePanel from "@/components/results/LiteraturePanel";

type TabId = "diagnosis" | "variants" | "structure" | "acmg" | "similar" | "literature" | "phenotypes";

export default function ResultsPage() {
  const [params] = useSearchParams();
  const caseId = params.get("case");
  const navigate = useNavigate();
  const [tab, setTab] = useState<TabId>("diagnosis");
  const [downloading, setDownloading] = useState(false);

  const { data: caseData, isLoading } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => axios.get(`/api/cases/${caseId}`).then((r) => r.data),
    enabled: !!caseId,
  });

  if (!caseId) {
    return (
      <Empty msg="No case selected." onAction={() => navigate("/cases")} actionLabel="Go to Cases" />
    );
  }
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }
  if (!caseData?.result && !caseData?.diagnoses) {
    return <Empty msg="This case has no results yet." onAction={() => navigate("/diagnose")} actionLabel="New Case" />;
  }

  const result = caseData.result || {};
  const deeprare = result.deeprare;
  const acmg = result.acmg;
  const prioritized = caseData.prioritized_variants || result.prioritized_variants || [];
  const structures = caseData.structures || result.structures || [];
  const similar = caseData.similar_cases || result.similar_cases || [];
  const literature = caseData.literature || result.literature || [];
  const phenotypes = caseData.phenotypes || result.phenotypes || [];
  const parentPheno = caseData.parent_phenotypes || result.parent_phenotypes || {};

  const top = deeprare?.candidates?.[0];
  const novelCount = prioritized.filter((v: any) => v.novel).length;

  const TABS: { id: TabId; label: string; icon: React.ElementType; count?: number }[] = [
    { id: "diagnosis", label: "Diagnosis", icon: Stethoscope },
    { id: "variants", label: "Variants", icon: ListFilter, count: prioritized.length },
    { id: "structure", label: "Structure", icon: Atom, count: structures.length },
    ...(acmg ? [{ id: "acmg" as TabId, label: "ACMG", icon: Brain }] : []),
    { id: "similar", label: "Similar Cases", icon: Users, count: similar.length },
    { id: "literature", label: "Literature", icon: BookOpen, count: literature.length },
    { id: "phenotypes", label: "Phenotypes", icon: Brain, count: phenotypes.length },
  ];

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(caseData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `raredx-${caseId}.json`; a.click();
    URL.revokeObjectURL(url);
    toast.success("JSON downloaded");
  };

  const downloadPDF = async () => {
    if (!result) return;
    setDownloading(true);
    try {
      const resp = await axios.post("/api/report/generate", {
        session_id: caseId, patient_name: result.patient_name || caseData.title,
        deeprare, acmg, alphafold: structures, summary: result.summary || "",
        time_to_diagnosis_estimate: "5–7 years → minutes",
      }, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = `raredx-${caseId}.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded");
    } catch { toast.error("PDF failed"); }
    finally { setDownloading(false); }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="card p-6 space-y-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">Diagnostic Results</h1>
            </div>
            <p className="text-sm text-slate-500">
              {result.patient_name || caseData.title}
              <span className="mx-2 text-slate-300">·</span>
              <span className="font-mono text-xs">{caseId.slice(0, 8)}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={downloadJSON} className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800">
              <FileText className="h-3.5 w-3.5" /> JSON
            </button>
            <button onClick={downloadPDF} disabled={downloading} className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-60 dark:bg-indigo-900/30 dark:text-indigo-300">
              <Download className="h-3.5 w-3.5" /> {downloading ? "…" : "PDF"}
            </button>
            <button onClick={() => navigate("/diagnose")} className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800">
              <RotateCcw className="h-3.5 w-3.5" /> New
            </button>
          </div>
        </div>

        {result.summary && (
          <div className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 p-4 text-white"
            dangerouslySetInnerHTML={{ __html: result.summary }} />
        )}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric icon={Stethoscope} label="Top Diagnosis" value={top?.disease_name ?? "—"} sub={top ? `${(top.score * 100).toFixed(0)}% conf.` : ""} />
          <Metric icon={ListFilter} label="Variants" value={String(prioritized.length)} sub={`${novelCount} novel`} />
          <Metric icon={Users} label="Similar Cases" value={String(similar.length)} sub="reference DB" />
          <Metric icon={Clock} label="Time Saved" value="5–7 yrs" sub="vs traditional" />
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border bg-white p-1 dark:bg-slate-900 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon, count }) => (
          <button key={id} onClick={() => setTab(id)}
            className={cn("flex flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
              tab === id ? "bg-slate-100 text-indigo-600 shadow-sm dark:bg-slate-800" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300")}>
            <Icon className="h-4 w-4" />
            {label}
            {count !== undefined && count > 0 && (
              <span className="rounded-full bg-slate-200 px-1.5 text-xs dark:bg-slate-700">{count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        {tab === "diagnosis" && (deeprare ? <DeepRarePanel result={deeprare} /> : <p className="text-slate-400 text-sm">No diagnosis data.</p>)}
        {tab === "variants" && <VariantsPanel variants={prioritized} />}
        {tab === "structure" && <AlphaFoldPanel results={structures} />}
        {tab === "acmg" && acmg && <ACMGPanel result={acmg} />}
        {tab === "similar" && <SimilarCasesPanel cases={similar} />}
        {tab === "literature" && <LiteraturePanel items={literature} />}
        {tab === "phenotypes" && <PhenotypesPanel phenotypes={phenotypes} parents={parentPheno} />}
      </motion.div>
    </div>
  );
}

function PhenotypesPanel({ phenotypes, parents }: { phenotypes: any[]; parents: any }) {
  return (
    <div className="space-y-4">
      <div className="card p-4">
        <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Patient HPO Profile</p>
        <div className="flex flex-wrap gap-2">
          {phenotypes.map((p, i) => (
            <span key={i} className={cn("rounded-full px-2.5 py-1 text-xs",
              p.hpo_id ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
                : "bg-slate-100 text-slate-500 dark:bg-slate-800")}>
              {p.term} {p.hpo_id && <span className="font-mono opacity-60">{p.hpo_id}</span>}
            </span>
          ))}
          {phenotypes.length === 0 && <span className="text-sm text-slate-400">No phenotypes resolved</span>}
        </div>
      </div>
      {["father", "mother"].map((parent) => (
        parents?.[parent]?.length > 0 && (
          <div key={parent} className="card p-4">
            <p className="mb-2 text-sm font-semibold capitalize text-slate-700 dark:text-slate-300">{parent} HPO Profile</p>
            <div className="flex flex-wrap gap-2">
              {parents[parent].map((p: any, i: number) => (
                <span key={i} className="rounded-full bg-violet-100 px-2.5 py-1 text-xs text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
                  {p.term} {p.hpo_id && <span className="font-mono opacity-60">{p.hpo_id}</span>}
                </span>
              ))}
            </div>
          </div>
        )
      ))}
    </div>
  );
}

function Metric({ icon: Icon, label, value, sub }: { icon: React.ElementType; label: string; value: string; sub: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
      <Icon className="mb-1.5 h-5 w-5 text-indigo-500" />
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-bold text-slate-900 dark:text-white text-sm leading-tight truncate">{value}</p>
      <p className="text-xs text-slate-400">{sub}</p>
    </div>
  );
}

function Empty({ msg, onAction, actionLabel }: { msg: string; onAction: () => void; actionLabel: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 space-y-4">
      <p className="text-slate-500">{msg}</p>
      <button onClick={onAction} className="gradient-brand rounded-xl px-5 py-2.5 text-sm font-semibold text-white">
        {actionLabel}
      </button>
    </div>
  );
}
