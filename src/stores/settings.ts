import { create } from "zustand";
import type { WaterMode } from "@/lib/waterApi";

interface SettingsState {
  includeHydro: boolean;
  mode: WaterMode;
  setIncludeHydro: (v: boolean) => void;
  setMode: (m: WaterMode) => void;
}

export const useSettings = create<SettingsState>((set) => ({
  includeHydro: false,
  mode: "origin",
  setIncludeHydro: (includeHydro) => set({ includeHydro }),
  setMode: (mode) => set({ mode }),
}));
