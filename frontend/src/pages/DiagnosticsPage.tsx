import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import PatientForm from "@/components/patient-form/PatientForm";
import PipelineStepper from "@/components/pipeline/PipelineStepper";
import { usePipelineStore } from "@/store/pipelineStore";
import type { PatientFormValues } from "@/types/patient";
import type { PipelineResult, SSEEvent } from "@/types/pipeline";
import { Dna, Sparkles } from "lucide-react";

export default function DiagnosticsPage() {
  const [searchParams] = useSearchParams();
  const demoId = searchParams.get("demo");
  const navigate = useNavigate();

  const { events, running, addEvent, setResult, setRunning, reset } = usePipelineStore();
  const [overallProgress, setOverallProgress] = useState(0);

  // Load demo case if ?demo= param present
  const { data: demoData } = useQuery({
    queryKey: ["demo", demoId],
    queryFn: () => axios.get(`/api/demo/cases/${demoId}`).then((r) => r.data),
    enabled: !!demoId,
  });

  const handleSubmit = async (data: PatientFormValues, file: File | null) => {
    reset();
    setRunning(true);

    // Create a case record in the database first
    let caseId: string | null = null;
    try {
      const patientName = `${data.first_name ?? ""} ${data.last_name ?? ""}`.trim();
      const caseTitle = patientName
        ? `${patientName} — ${new Date().toLocaleDateString()}`
        : `Case ${new Date().toLocaleDateString()}`;
      const caseResp = await axios.post("/api/cases", {
        title: caseTitle,
        patient_data: { ...data, symptoms: data.symptoms ?? [], suspected_diseases: data.suspected_diseases ?? [] },
      });
      caseId = caseResp.data.id as string;
    } catch {
      // Non-fatal: pipeline can still run without a persisted case
    }

    const formData = new FormData();
    // Only attach VCF if the user actually uploaded one
    if (file && file.size > 0) {
      formData.append("vcf_file", file);
    }
    formData.append(
      "patient_json",
      JSON.stringify({
        ...data,
        symptoms: data.symptoms ?? [],
        suspected_diseases: data.suspected_diseases ?? [],
      })
    );
    if (caseId) {
      formData.append("case_id", caseId);
    }

    try {
      const response = await fetch("/api/pipeline/run", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
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

            if (evt.stage === "complete" && evt.data) {
              const result = evt.data as unknown as PipelineResult;
              setResult(result);
              setRunning(false);
              toast.success("Pipeline complete!", { description: `Top diagnosis: ${result.deeprare?.candidates?.[0]?.disease_name}` });
              navigate("/results");
            }

            if (evt.stage === "error") {
              setRunning(false);
              toast.error("Pipeline failed", { description: evt.message });
            }
          } catch {
            // skip malformed event
          }
        }
      }
    } catch (err) {
      setRunning(false);
      toast.error("Connection error", { description: String(err) });
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Dna className="h-5 w-5 text-indigo-600" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            New Diagnostic Case
          </h1>
          {demoId && (
            <span className="flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              <Sparkles className="h-3 w-3" /> Demo: {demoId}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-500">
          Fill in patient information and upload a VCF file. The AI pipeline will run automatically.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Form */}
        <div className="lg:col-span-2">
          <div className="card p-6">
            <PatientForm
              defaultValues={demoData ?? undefined}
              onSubmit={handleSubmit}
              loading={running}
            />
          </div>
        </div>

        {/* Pipeline sidebar */}
        <div className="space-y-4">
          {running || events.length > 0 ? (
            <div className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
                Pipeline Status
              </h2>
              <PipelineStepper events={events} overallProgress={overallProgress} />
            </div>
          ) : (
            <div className="card p-6 text-center text-slate-400 space-y-2">
              <Dna className="mx-auto h-10 w-10 opacity-30" />
              <p className="text-sm">Pipeline will run here after submission</p>
              <p className="text-xs">Takes ~8–10 seconds with mock data</p>
            </div>
          )}

          {/* Legend */}
          <div className="card p-4 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pipeline Steps</p>
            {[
              ["VCF Parse", "Extracts variants from your file"],
              ["DeepRare", "Ranks diseases by phenotype + genotype"],
              ["ACMG", "Classifies each variant's pathogenicity"],
              ["AlphaFold3", "Predicts 3D protein structural impact"],
            ].map(([name, desc]) => (
              <div key={name} className="flex gap-2 text-xs">
                <span className="font-semibold text-indigo-600 w-20 flex-shrink-0">{name}</span>
                <span className="text-slate-500">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
