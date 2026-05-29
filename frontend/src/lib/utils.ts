import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ACMGClassification } from "@/types/pipeline";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function classificationBadge(cls: ACMGClassification): string {
  const map: Record<ACMGClassification, string> = {
    Pathogenic: "badge-pathogenic",
    "Likely Pathogenic": "badge-likely-pathogenic",
    "Variant of Uncertain Significance": "badge-vus",
    "Likely Benign": "badge-benign",
    Benign: "badge-benign",
  };
  return map[cls] ?? "badge-benign";
}

export function severityColor(severity: "High" | "Medium" | "Low"): string {
  return severity === "High"
    ? "text-red-600 dark:text-red-400"
    : severity === "Medium"
      ? "text-orange-500 dark:text-orange-400"
      : "text-green-600 dark:text-green-400";
}

export function formatAF(af: number): string {
  if (af === 0) return "Not in gnomAD";
  if (af < 0.0001) return `${(af * 1_000_000).toFixed(1)} per million`;
  return `${(af * 100).toFixed(4)}%`;
}

export function scoreToPercent(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}
