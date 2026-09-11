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

  const hasData = (p?.rows ?? 0) > 0;

  return (
    <header className="flex items-center gap-6 border-b border-border bg-card px-5 py-3">
      <div className="shrink-0">
        <h1 className="text-lg font-bold leading-tight tracking-tight">Grid Conductor</h1>
        <p className="text-xs text-muted-foreground">
          Your real time intelligent engine&nbsp;
        </p>
      </div>

      <ol className="flex items-center gap-2">
        <li className="flex items-center gap-2">
          <StepBadge n={1} active={!hasData} done={hasData} />
          <div className="flex flex-col gap-1">
            <Button
              size="sm"
              variant={hasData ? "secondary" : "default"}
              onClick={startImport}
              disabled={running}
              className={hasData ? "" : "shadow-md"}
            >
              {running ? "Importing…" : hasData ? "Re-import year" : "Import year"}
            </Button>
            <div className="w-36">
              <Progress value={Math.round((p?.fraction ?? 0) * 100)} />
              <p className="mt-0.5 text-[10px] text-muted-foreground">
                {p?.rows
                  ? `${p.rows.toLocaleString()} rows · ${p.done}/${p.total} jobs`
                  : "No data yet"}
                {p?.paused ? " · paused" : ""}
              </p>
            </div>
          </div>
        </li>
        <StepArrow />
        <li className="flex items-center gap-2">
          <StepBadge n={2} active={hasData} done={false} />
          <Button
            size="sm"
            variant={hasData ? "default" : "secondary"}
            onClick={() => detect.mutate()}
            disabled={detect.isPending}
            className={hasData ? "shadow-md" : ""}
          >
            {detect.isPending ? "Analysing…" : "Find targets"}
          </Button>
        </li>
        <StepArrow />
        <li className="flex items-center gap-2">
          <StepBadge n={3} active={false} done={false} />
          <p className="max-w-36 text-xs font-medium text-primary">
            Click a highlighted border on the map
          </p>
        </li>
      </ol>

      <div className="ml-auto flex items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Colour by
        </span>
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

function StepBadge({ n, active, done }: { n: number; active: boolean; done: boolean }) {
  return (
    <span
      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
        done
          ? "bg-primary/15 text-primary"
          : active
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
      }`}
    >
      {n}
    </span>
  );
}

function StepArrow() {
  return <span className="mx-1 text-muted-foreground/50">→</span>;
}
