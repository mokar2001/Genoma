import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, ChevronLeft, Loader2, Dna } from "lucide-react";
import { cn } from "@/lib/utils";
import { ETHNICITIES, FAMILIAL_TYPES, SEXES, type PatientFormValues } from "@/types/patient";
import VcfUploader from "./VcfUploader";
import ParentSection from "./ParentSection";
import SymptomsInput from "./SymptomsInput";

const schema = z.object({
  first_name: z.string().min(1, "Required"),
  last_name: z.string().min(1, "Required"),
  date_of_birth: z.string().min(1, "Required"),
  sex: z.enum(SEXES),
  ethnicity: z.enum(ETHNICITIES),
  symptoms: z.array(z.string()).min(1, "Add at least one symptom"),
  suspected_diseases: z.array(z.string()).default([]),
  clinical_notes: z.string().optional(),
  age_of_onset: z.coerce.number().int().positive().optional().or(z.literal("")),
  familial_type: z.enum(FAMILIAL_TYPES),
  consanguinity: z.boolean().default(false),
  affected_siblings_count: z.coerce.number().int().min(0).default(0),
  father: z
    .object({
      is_affected: z.boolean(),
      age: z.coerce.number().int().positive().optional().or(z.literal("")),
      age_of_onset: z.coerce.number().int().positive().optional().or(z.literal("")),
      known_conditions: z.string().optional(),
      phenotype_description: z.string().optional(),
      is_deceased: z.boolean(),
      cause_of_death: z.string().optional(),
    })
    .optional(),
  mother: z
    .object({
      is_affected: z.boolean(),
      age: z.coerce.number().int().positive().optional().or(z.literal("")),
      age_of_onset: z.coerce.number().int().positive().optional().or(z.literal("")),
      known_conditions: z.string().optional(),
      phenotype_description: z.string().optional(),
      is_deceased: z.boolean(),
      cause_of_death: z.string().optional(),
    })
    .optional(),
});

const STEPS = [
  { id: "demographics", label: "Patient Info" },
  { id: "clinical", label: "Clinical" },
  { id: "family", label: "Family" },
  { id: "genetics", label: "Genomics" },
];

interface Props {
  defaultValues?: Partial<PatientFormValues>;
  onSubmit: (data: PatientFormValues, file: File) => void;
  loading?: boolean;
}

export default function PatientForm({ defaultValues, onSubmit, loading }: Props) {
  const [step, setStep] = useState(0);
  const [vcfFile, setVcfFile] = useState<File | null>(null);

  const form = useForm<PatientFormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      sex: "Male",
      ethnicity: "White",
      familial_type: "Unknown / Suspected familial",
      consanguinity: false,
      affected_siblings_count: 0,
      symptoms: [],
      suspected_diseases: [],
      ...defaultValues,
    },
  });

  const { register, handleSubmit, watch, setValue, formState: { errors } } = form;

  const handleFinalSubmit = (data: PatientFormValues) => {
    if (!vcfFile) {
      // Create a minimal mock VCF file for demo
      const blob = new Blob(["##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"], {
        type: "text/plain",
      });
      const mockFile = new File([blob], "demo.vcf", { type: "text/plain" });
      onSubmit(data, mockFile);
    } else {
      onSubmit(data, vcfFile);
    }
  };

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setStep(i)}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all",
                i < step
                  ? "bg-indigo-600 text-white"
                  : i === step
                    ? "bg-indigo-600 text-white ring-4 ring-indigo-100 dark:ring-indigo-900"
                    : "bg-slate-100 text-slate-400 dark:bg-slate-800"
              )}
            >
              {i + 1}
            </button>
            <span
              className={cn(
                "hidden text-xs font-medium sm:block",
                i === step ? "text-indigo-600" : "text-slate-400"
              )}
            >
              {s.label}
            </span>
            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  "h-px w-6 sm:w-12",
                  i < step ? "bg-indigo-600" : "bg-slate-200 dark:bg-slate-700"
                )}
              />
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit(handleFinalSubmit)} className="space-y-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {/* ── Step 0: Demographics ─────────────────────────────────── */}
            {step === 0 && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                  Patient Demographics
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="First Name" error={errors.first_name?.message}>
                    <input {...register("first_name")} className={inputCls(!!errors.first_name)} placeholder="James" />
                  </Field>
                  <Field label="Last Name" error={errors.last_name?.message}>
                    <input {...register("last_name")} className={inputCls(!!errors.last_name)} placeholder="Hartwell" />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Date of Birth" error={errors.date_of_birth?.message}>
                    <input {...register("date_of_birth")} type="date" className={inputCls(!!errors.date_of_birth)} />
                  </Field>
                  <Field label="Biological Sex">
                    <select {...register("sex")} className={inputCls(false)}>
                      {SEXES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </Field>
                </div>
                <Field label="Race / Ethnicity">
                  <select {...register("ethnicity")} className={inputCls(false)}>
                    {ETHNICITIES.map((e) => <option key={e}>{e}</option>)}
                  </select>
                </Field>
              </div>
            )}

            {/* ── Step 1: Clinical ─────────────────────────────────────── */}
            {step === 1 && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                  Clinical Presentation
                </h3>
                <SymptomsInput
                  label="Symptoms / Phenotype Terms (HPO)"
                  value={watch("symptoms")}
                  onChange={(v) => setValue("symptoms", v)}
                  placeholder="e.g. Arachnodactyly, Ectopia lentis…"
                  error={(errors.symptoms as any)?.message}
                />
                <SymptomsInput
                  label="Suspected Diseases (optional)"
                  value={watch("suspected_diseases")}
                  onChange={(v) => setValue("suspected_diseases", v)}
                  placeholder="e.g. Marfan syndrome, Loeys-Dietz…"
                />
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Age of Onset (years)">
                    <input
                      {...register("age_of_onset")}
                      type="number"
                      min={0}
                      className={inputCls(false)}
                      placeholder="14"
                    />
                  </Field>
                </div>
                <Field label="Clinical Notes">
                  <textarea
                    {...register("clinical_notes")}
                    rows={3}
                    className={inputCls(false)}
                    placeholder="Relevant clinical context, imaging findings, lab values…"
                  />
                </Field>
              </div>
            )}

            {/* ── Step 2: Family History ────────────────────────────────── */}
            {step === 2 && (
              <div className="space-y-5">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                  Family History
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Inheritance Pattern">
                    <select {...register("familial_type")} className={inputCls(false)}>
                      {FAMILIAL_TYPES.map((f) => <option key={f}>{f}</option>)}
                    </select>
                  </Field>
                  <Field label="Affected Siblings">
                    <input
                      {...register("affected_siblings_count")}
                      type="number"
                      min={0}
                      className={inputCls(false)}
                    />
                  </Field>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input {...register("consanguinity")} type="checkbox" className="h-4 w-4 rounded accent-indigo-600" />
                  <span>Parental consanguinity (common ancestors)</span>
                </label>

                <ParentSection label="Father" prefix="father" register={register} watch={watch} setValue={setValue} />
                <ParentSection label="Mother" prefix="mother" register={register} watch={watch} setValue={setValue} />
              </div>
            )}

            {/* ── Step 3: Genomics ─────────────────────────────────────── */}
            {step === 3 && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                  Genomic Data
                </h3>
                <VcfUploader file={vcfFile} onFile={setVcfFile} />
                <p className="text-xs text-slate-500">
                  If no VCF is uploaded, the pipeline will use demo variant data matched to your symptoms.
                </p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={back}
            disabled={step === 0}
            className="flex items-center gap-1 rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ChevronLeft className="h-4 w-4" /> Back
          </button>

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={next}
              className="gradient-brand flex items-center gap-1 rounded-lg px-5 py-2 text-sm font-semibold text-white"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={loading}
              className="gradient-brand flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 disabled:opacity-70"
            >
              {loading ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Running Pipeline…</>
              ) : (
                <><Dna className="h-4 w-4" /> Run Diagnostic Pipeline</>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

function inputCls(hasError: boolean) {
  return cn(
    "w-full rounded-lg border px-3 py-2 text-sm outline-none transition",
    "bg-white dark:bg-slate-800 dark:text-slate-100",
    "focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
    hasError ? "border-red-400" : "border-slate-300 dark:border-slate-600"
  );
}
