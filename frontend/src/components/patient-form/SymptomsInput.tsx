import { useState, KeyboardEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  error?: string;
}

export default function SymptomsInput({ label, value, onChange, placeholder, error }: Props) {
  const [input, setInput] = useState("");

  const add = () => {
    const trimmed = input.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setInput("");
  };

  const remove = (item: string) => onChange(value.filter((v) => v !== item));

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") { e.preventDefault(); add(); }
    if (e.key === "Backspace" && !input && value.length > 0) remove(value[value.length - 1]);
  };

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</label>
      <div
        className={cn(
          "flex min-h-[2.75rem] flex-wrap gap-1.5 rounded-lg border px-2.5 py-2",
          "bg-white dark:bg-slate-800",
          "focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-indigo-500",
          error ? "border-red-400" : "border-slate-300 dark:border-slate-600"
        )}
      >
        {value.map((item) => (
          <span
            key={item}
            className="flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
          >
            {item}
            <button type="button" onClick={() => remove(item)} className="hover:text-red-500">
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          className="min-w-[120px] flex-1 bg-transparent text-sm text-slate-900 outline-none dark:text-slate-100 placeholder:text-slate-400"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          onBlur={add}
          placeholder={value.length === 0 ? placeholder : "Add more…"}
        />
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <p className="text-xs text-slate-400">Press Enter or comma to add. Backspace to remove.</p>
    </div>
  );
}
