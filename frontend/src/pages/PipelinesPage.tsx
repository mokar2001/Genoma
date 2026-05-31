import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { motion } from "framer-motion";
import { Workflow, Download, CheckCircle2, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface Pipeline {
  name: string;
  title: string;
  description: string;
  input: string;
  output: string;
  recommended: boolean;
  installed: boolean;
}

export default function PipelinesPage() {
  const qc = useQueryClient();
  const { data: registry = [], isLoading } = useQuery<Pipeline[]>({
    queryKey: ["pipelines-registry"],
    queryFn: () => axios.get("/api/pipelines/registry").then((r) => r.data),
    refetchInterval: 5000,
  });

  const [installing, setInstalling] = useState<string | null>(null);

  const install = useMutation({
    mutationFn: (name: string) => {
      setInstalling(name);
      // nextflow pull can take a couple of minutes — allow a long client timeout
      return axios.post("/api/pipelines/install", { name }, { timeout: 290000 });
    },
    onSuccess: (_, name) => {
      toast.success(`${name} installed`, { description: "Pipeline pulled and ready to run." });
      qc.invalidateQueries({ queryKey: ["pipelines-registry"] });
    },
    onError: (err: any, name) => {
      const detail = err?.response?.data?.detail || err?.message || "Unknown error";
      toast.error(`Failed to install ${name}`, { description: String(detail).slice(0, 200) });
    },
    onSettled: () => setInstalling(null),
  });

  if (isLoading) {
    return <div className="flex items-center justify-center py-24"><Loader2 className="h-8 w-8 animate-spin text-indigo-500" /></div>;
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <Workflow className="h-5 w-5 text-indigo-600" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Bioinformatics Pipelines</h1>
        </div>
        <p className="text-sm text-slate-500">
          Install nf-core pipelines on demand. Once installed, a case with FASTQ/BAM input can run them to produce a VCF.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {registry.map((p, i) => (
          <motion.div key={p.name} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }} className="card p-5 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 dark:text-white">{p.title}</span>
                  {p.recommended && (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                      Recommended
                    </span>
                  )}
                </div>
                <p className="font-mono text-xs text-indigo-600 dark:text-indigo-400">{p.name}</p>
              </div>
              {p.installed ? (
                <span className="flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-300">
                  <CheckCircle2 className="h-3 w-3" /> Installed
                </span>
              ) : (
                <button onClick={() => install.mutate(p.name)} disabled={install.isPending}
                  className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
                  {installing === p.name ? (
                    <><Loader2 className="h-3 w-3 animate-spin" /> Installing…</>
                  ) : (
                    <><Download className="h-3 w-3" /> Install</>
                  )}
                </button>
              )}
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">{p.description}</p>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800">{p.input}</span>
              <ArrowRight className="h-3 w-3" />
              <span className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800">{p.output}</span>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
        <strong>Note:</strong> Real Nextflow execution requires the worker container with the
        Docker socket mounted. WGS runs are resource-heavy — capped to your server's 28&nbsp;GB / 7&nbsp;cores.
      </div>
    </div>
  );
}
