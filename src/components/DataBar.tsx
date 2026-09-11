import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { getImportProgress, planImport, runImportBatch } from "@/lib/import.functions";
import { refreshOfficialCapacity, refreshTargets } from "@/lib/analysis.functions";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export function DataBar({
  metric,
  onMetricChange,
}: {
  metric: "market" | "climate";
  onMetricChange: (m: "market" | "climate") => void;
}) {
  const qc = useQueryClient();
  const progressFn = useServerFn(getImportProgress);
  const plan = useServerFn(planImport);
  const runBatch = useServerFn(runImportBatch);
  const targetsFn = useServerFn(refreshTargets);
  const ntcFn = useServerFn(refreshOfficialCapacity);
  const [running, setRunning] = useState(false);
  const stop = useRef(false);

  const progress = useQuery({
    queryKey: ["import-progress"],
    queryFn: () => progressFn(),
    refetchInterval: running ? 4000 : false,
  });

  useEffect(() => () => void (stop.current = true), []);

  async function startImport() {
    stop.current = false;
    setRunning(true);
    try {
      await plan();
      for (let i = 0; i < 2000 && !stop.current; i++) {
        const res = (await runBatch({ data: { chunks: 8 } })) as {
          complete?: boolean;
          throttled?: boolean;
          skipped?: string;
          reason?: string | null;
        };
        qc.invalidateQueries({ queryKey: ["import-progress"] });
        if (res?.skipped === "paused" || res?.throttled) {
          toast.warning(res?.reason ?? "Import paused by the data provider's limits");
          break;
        }
        if (res?.complete) {
          toast.success("Historical data imported");
          break;
        }
      }
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setRunning(false);
      qc.invalidateQueries({ queryKey: ["import-progress"] });
    }
  }

  const detect = useMutation({
    mutationFn: async () => {
      const t = await targetsFn();
      await ntcFn().catch(() => null);
      return t;
    },
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ["targets"] });
      qc.invalidateQueries({ queryKey: ["zones"] });
      toast.success(`${t.targets} borders analysed`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const p = progress.data;

  return (
    <header className="flex items-center gap-4 border-b border-border bg-card px-4 py-3">
      <div>
        <h1 className="text-sm font-semibold">EU cross-border opportunity workbench</h1>
        <p className="text-xs text-muted-foreground">
          One year of hourly European market data, congested borders, and investment scenarios.
        </p>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="w-44">
          <Progress value={Math.round((p?.fraction ?? 0) * 100)} />
          <p className="mt-1 text-[11px] text-muted-foreground">
            {p?.rows ? `${p.rows.toLocaleString()} rows · ${p.done}/${p.total} jobs` : "No data yet"}
            {p?.paused ? " · paused" : ""}
          </p>
        </div>
        <Button size="sm" variant="secondary" onClick={startImport} disabled={running}>
          {running ? "Importing…" : "Import year"}
        </Button>
        <Button size="sm" onClick={() => detect.mutate()} disabled={detect.isPending}>
          {detect.isPending ? "Analysing…" : "Find targets"}
        </Button>
        <div className="flex rounded-md border border-border p-0.5 text-xs">
          {(["market", "climate"] as const).map((m) => (
            <button
              key={m}
              onClick={() => onMetricChange(m)}
              className={`rounded px-2 py-1 ${
                metric === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              {m === "market" ? "Market" : "Climate"}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
