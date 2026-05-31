import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import { Dna, Sparkles } from "lucide-react";
import PatientForm from "@/components/patient-form/PatientForm";
import PipelineStepper from "@/components/pipeline/PipelineStepper";
import { usePipelineStore } from "@/store/pipelineStore";
import { useAuthStore } from "@/store/authStore";
import type { PatientFormValues } from "@/types/patient";
import type { SSEEvent } from "@/types/pipeline";

export default function DiagnosticsPage() {
  const [searchParams] = useSearchParams();
  const demoId = searchParams.get("demo");
  const navigate = useNavigate();
  const { token } = useAuthStore();

  const { events, running, addEvent, setRunning, reset } = usePipelineStore();
  const [overallProgress, setOverallProgress] = useState(0);

  const { data: demoData } = useQuery({
    queryKey: ["demo", demoId],
    queryFn: () => axios.get(`/api/demo/cases/${demoId}`).then((r) => r.data),
    enabled: !!demoId,
  });

  const handleSubmit = async (data: PatientFormValues, file: File | null) => {
    reset();
    setRunning(true);
    setOverallProgress(0);

    try {
      // 1. Create the case
      const patientName = `${data.first_name ?? ""} ${data.last_name ?? ""}`.trim();
      const title = patientName
        ? `${patientName} — ${new Date().toLocaleDateString()}`
        : `Case ${new Date().toLocaleDateString()}`;

      const { data: created } = await axios.post("/api/cases", {
        title,
        patient_data: {
          ...data,
          symptoms: data.symptoms ?? [],
          suspected_diseases: data.suspected_diseases ?? [],
        },
      });
      const caseId: string = created.id;

      // 2. Upload genomic file (if any)
      if (file && file.size > 0) {
        const fd = new FormData();
        fd.append("file", file);
        toast.info("Uploading genomic file…");
        await axios.post(`/api/cases/${caseId}/upload`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      // 3. Kick off the pipeline
      await axios.post(`/api/cases/${caseId}/run`);

      // 4. Stream live progress via SSE (fetch — to send the auth header)
      const resp = await fetch(`/api/cases/${caseId}/stream`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.body) throw new Error("No stream");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt: SSEEvent = JSON.parse(line.slice(6));
            addEvent(evt);
            setOverallProgress(evt.progress);
            if (evt.stage === "complete") {
              setRunning(false);
              toast.success("Pipeline complete!");
              navigate(`/results?case=${caseId}`);
              return;
            }
            if (evt.stage === "error") {
              setRunning(false);
              toast.error("Pipeline failed", { description: evt.message });
              return;
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: any) {
      setRunning(false);
      toast.error("Failed to start case", {
        description: err?.response?.data?.detail || String(err),
      });
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Dna className="h-5 w-5 text-indigo-600" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">New Diagnostic Case</h1>
          {demoId && (
            <span className="flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              <Sparkles className="h-3 w-3" /> Demo: {demoId}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-500">
          Enter patient + family history, upload a genomic file (VCF / FASTQ / BAM),
          and the pipeline runs end-to-end.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="card p-6">
            <PatientForm defaultValues={demoData ?? undefined} onSubmit={handleSubmit} loading={running} />
          </div>
        </div>

        <div className="space-y-4">
          {running || events.length > 0 ? (
            <div className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Pipeline Status</h2>
              <PipelineStepper events={events} overallProgress={overallProgress} />
            </div>
          ) : (
            <div className="card p-6 text-center text-slate-400 space-y-2">
              <Dna className="mx-auto h-10 w-10 opacity-30" />
              <p className="text-sm">Pipeline runs here after you submit</p>
              <p className="text-xs">FASTQ triggers real nf-core/sarek (can take hours); VCF is instant</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
