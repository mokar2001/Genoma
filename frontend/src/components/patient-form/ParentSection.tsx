import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UseFormRegister, UseFormWatch, UseFormSetValue } from "react-hook-form";
import type { PatientFormValues } from "@/types/patient";

interface Props {
  label: "Father" | "Mother";
  prefix: "father" | "mother";
  register: UseFormRegister<PatientFormValues>;
  watch: UseFormWatch<PatientFormValues>;
  setValue: UseFormSetValue<PatientFormValues>;
}

export default function ParentSection({ label, prefix, register, watch, setValue }: Props) {
  const [open, setOpen] = useState(false);
  const parent = watch(prefix) as any;

  return (
    <div className="rounded-xl border dark:border-slate-700">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{label}</span>
          {parent?.is_affected && (
            <span className="badge-likely-pathogenic">Affected</span>
          )}
          {parent?.is_deceased && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800">Deceased</span>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {open && (
        <div className="space-y-3 border-t px-4 pb-4 pt-3 dark:border-slate-700">
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                {...register(`${prefix}.is_affected`)}
                className="h-4 w-4 rounded accent-indigo-600"
              />
              Affected
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                {...register(`${prefix}.is_deceased`)}
                className="h-4 w-4 rounded accent-indigo-600"
              />
              Deceased
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Current Age</label>
              <input
                {...register(`${prefix}.age`)}
                type="number"
                min={0}
                placeholder="52"
                className={inputCls}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Age of Onset</label>
              <input
                {...register(`${prefix}.age_of_onset`)}
                type="number"
                min={0}
                placeholder="18"
                className={inputCls}
              />
            </div>
          </div>

          {parent?.is_deceased && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Cause of Death</label>
              <input
                {...register(`${prefix}.cause_of_death`)}
                placeholder="e.g. Aortic dissection"
                className={inputCls}
              />
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500">Known Conditions</label>
            <input
              {...register(`${prefix}.known_conditions`)}
              placeholder="Diagnosed conditions, surgeries…"
              className={inputCls}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500">Phenotype Description</label>
            <textarea
              {...register(`${prefix}.phenotype_description`)}
              rows={2}
              placeholder="Physical features, symptoms, clinical observations…"
              className={inputCls}
            />
          </div>
        </div>
      )}
    </div>
  );
}

const inputCls =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100";
