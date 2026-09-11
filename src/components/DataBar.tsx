import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useRef, useState } from "react";
import { Settings } from "lucide-react";
import { toast } from "sonner";
import { getImportProgress, planImport, runImportBatch } from "@/lib/import.functions";
import { refreshOfficialCapacity, refreshTargets } from "@/lib/analysis.functions";

export function DataBar({ step }: { step: 1 | 2 | 3 }) {
  const qc = useQueryClient();
  const progressFn = useServerFn(getImportProgress);
  const plan = useServerFn(planImport);
  const runBatch = useServerFn(runImportBatch);
  const targetsFn = useServerFn(refreshTargets);
  const ntcFn = useServerFn(refreshOfficialCapacity);
  const [running, setRunning] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const stop = useRef(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const progress = useQuery({
    queryKey: ["import-progress"],
    queryFn: () => progressFn(),
    refetchInterval: running ? 4000 : false,
  });

  useEffect(() => () => void (stop.current = true), []);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpen]);

  async function startImport() {
    setMenuOpen(false);
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

  const steps = [
    { n: 1, label: "Choose bottleneck", hint: "Click a highlighted border on the map" },
    { n: 2, label: "Simulate scenarios", hint: "Build scenarios in the left panel" },
    { n: 3, label: "Evaluate opportunity", hint: "Review results in the right panel" },
  ] as const;

  return (
    <header className="flex items-center gap-6 border-b border-border bg-card px-5 py-3">
      <div className="shrink-0">
        <h1 className="text-lg font-bold leading-tight tracking-tight">Grid Conductor</h1>
        <p className="text-xs text-muted-foreground">Your real time intelligent engine&nbsp;</p>
      </div>

      <ol className="flex flex-1 items-center justify-center gap-8">
        {steps.map((s) => {
          const active = step === s.n;
          const done = step > s.n;
          return (
            <li
              key={s.n}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 transition-colors ${
                active ? "bg-[#39FF14] text-black shadow-sm" : ""
              }`}
              title={s.hint}
              aria-current={active ? "step" : undefined}
            >
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${
                  active
                    ? "bg-black/80 text-[#39FF14]"
                    : done
                      ? "bg-primary/20 text-primary"
                      : "bg-muted text-muted-foreground"
                }`}
              >
                {s.n}
              </span>
              <span
                className={`text-xs font-medium ${
                  active ? "text-black" : done ? "text-foreground" : "text-muted-foreground"
                }`}
              >
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>


      <div className="relative ml-auto" ref={menuRef}>
        <button
          type="button"
          aria-label="Settings"
          onClick={() => setMenuOpen((o) => !o)}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <Settings className="h-4 w-4" />
        </button>
        {menuOpen && (
          <div className="absolute right-0 top-9 z-20 w-52 rounded-md border border-border bg-popover p-1 text-sm shadow-md">
            <button
              type="button"
              onClick={startImport}
              disabled={running}
              className="w-full rounded-sm px-2 py-1.5 text-left hover:bg-accent disabled:opacity-50"
            >
              {running ? "Importing…" : "Re-import year"}
              <span className="block text-[11px] text-muted-foreground">
                Troubleshooting only — runs daily automatically
              </span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                detect.mutate();
              }}
              disabled={detect.isPending}
              className="w-full rounded-sm px-2 py-1.5 text-left hover:bg-accent disabled:opacity-50"
            >
              {detect.isPending ? "Recomputing…" : "Recompute targets"}
              <span className="block text-[11px] text-muted-foreground">
                Re-run congestion and loss detection
              </span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
