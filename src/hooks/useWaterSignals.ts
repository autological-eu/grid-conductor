import { useQuery } from "@tanstack/react-query";
import { callWaterSignals, type BenchmarkResponse, type SeriesResponse, type WaterMode } from "@/lib/waterApi";
import { useSettings } from "@/stores/settings";

export interface SignalOptions {
  includeHydro?: boolean;
  mode?: WaterMode;
  jobHours?: number;
  enabled?: boolean;
}

export function useGlobalOptions() {
  const includeHydro = useSettings((s) => s.includeHydro);
  const mode = useSettings((s) => s.mode);
  return { includeHydro, mode };
}

export function useLatest(zone: string, o: SignalOptions = {}) {
  const g = useGlobalOptions();
  const includeHydro = o.includeHydro ?? g.includeHydro;
  const mode = o.mode ?? g.mode;
  return useQuery({
    queryKey: ["water", "latest", zone, includeHydro, mode],
    queryFn: () => callWaterSignals<SeriesResponse>({ action: "latest", zone, includeHydro, mode }),
    staleTime: 5 * 60 * 1000,
    enabled: o.enabled ?? true,
    retry: false,
  });
}

export function useHistory(zone: string, o: SignalOptions = {}) {
  const g = useGlobalOptions();
  const includeHydro = o.includeHydro ?? g.includeHydro;
  const mode = o.mode ?? g.mode;
  return useQuery({
    queryKey: ["water", "history", zone, includeHydro, mode],
    queryFn: () => callWaterSignals<SeriesResponse>({ action: "history", zone, includeHydro, mode }),
    staleTime: 15 * 60 * 1000,
    enabled: o.enabled ?? true,
    retry: false,
  });
}

export function useForecast(zone: string, o: SignalOptions = {}) {
  const g = useGlobalOptions();
  const includeHydro = o.includeHydro ?? g.includeHydro;
  const jobHours = o.jobHours ?? 4;
  return useQuery({
    queryKey: ["water", "forecast", zone, includeHydro, jobHours],
    queryFn: () =>
      callWaterSignals<SeriesResponse>({
        action: "forecast",
        zone,
        horizonHours: 72,
        jobHours,
        includeHydro,
      }),
    staleTime: 15 * 60 * 1000,
    enabled: o.enabled ?? true,
    retry: false,
  });
}

export function useBenchmark(zones: string[], days = 30) {
  return useQuery({
    queryKey: ["water", "benchmark", zones.join(","), days],
    queryFn: () => callWaterSignals<BenchmarkResponse>({ action: "benchmark", zones, days }),
    staleTime: 6 * 60 * 60 * 1000,
    retry: false,
  });
}
