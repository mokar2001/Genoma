import { create } from "zustand";
import type { PipelineResult, SSEEvent } from "@/types/pipeline";

interface PipelineState {
  events: SSEEvent[];
  result: PipelineResult | null;
  running: boolean;
  addEvent: (e: SSEEvent) => void;
  setResult: (r: PipelineResult) => void;
  setRunning: (v: boolean) => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  events: [],
  result: null,
  running: false,
  addEvent: (e) => set((s) => ({ events: [...s.events, e] })),
  setResult: (r) => set({ result: r }),
  setRunning: (v) => set({ running: v }),
  reset: () => set({ events: [], result: null, running: false }),
}));
