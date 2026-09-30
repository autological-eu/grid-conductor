import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { parseNetworkInput, type NetworkInput } from "@/lib/network-model/schema";
import {
  applyIntervention,
  type Intervention,
  type DispatchResult,
  type compareDispatch,
} from "@/lib/network-model/solver";
import { publicAsset } from "@/lib/research";
import { loadNetworkWorkspace, saveNetworkWorkspace } from "@/lib/network-model/persistence";

export const Route = createFileRoute("/network")({ component: NetworkLab });
type Result = {
  input_sha256: string;
  model_version: string;
  baseline: DispatchResult;
  scenario: DispatchResult;
  comparison: ReturnType<typeof compareDispatch>;
  elapsed_ms: number;
  baseline_cached: boolean;
};
const emptyPatch: Intervention = { edge_additions_mw: {}, storage: [] };

function NetworkLab() {
  const [input, setInput] = useState<NetworkInput>();
  const [patch, setPatch] = useState<Intervention>(emptyPatch);
  const [result, setResult] = useState<Result>();
  const [message, setMessage] = useState("Import a complete model input to start.");
  const [busy, setBusy] = useState(false);
  const [loadingInput, setLoadingInput] = useState(false);
  const [ready, setReady] = useState(false);
  const [edge, setEdge] = useState("");
  const [mw, setMw] = useState(100);
  const [zone, setZone] = useState("");
  const worker = useRef<Worker | null>(null);
  useEffect(() => {
    let active = true;
    void loadNetworkWorkspace()
      .then((saved) => {
        if (saved && active) {
          const data = parseNetworkInput(saved.input);
          applyIntervention(data, saved.patch);
          setInput(data);
          setPatch(saved.patch);
          setEdge(data.edges[0]?.id ?? "");
          setZone(data.zones[0] ?? "");
          setMessage(
            "Restored browser-local input and interventions. Re-run to obtain current solver results.",
          );
        }
      })
      .catch((error: unknown) => {
        if (active) setMessage(`Local storage could not be restored: ${String(error)}`);
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
      worker.current?.terminate();
    };
  }, []);
  useEffect(() => {
    if (!ready || !input) return;
    void saveNetworkWorkspace({ input, patch }).catch((error: unknown) =>
      setMessage(`Persistence failed: ${String(error)}`),
    );
  }, [input, patch, ready]);
  const importModel = (value: unknown) => {
    const data = parseNetworkInput(value);
    setInput(data);
    setPatch(emptyPatch);
    setResult(undefined);
    setEdge(data.edges.find((e) => e.id === "dc:14823")?.id ?? data.edges[0]?.id ?? "");
    setZone(data.zones.find((z) => z === "PL1 0") ?? data.zones[0] ?? "");
    setMessage("Input parsed. Source declaration is not independent validation.");
    worker.current?.terminate();
    worker.current = null;
  };
  const edit = (next: Intervention) => {
    if (!input) return;
    try {
      applyIntervention(input, next);
      setPatch(next);
      setResult(undefined);
    } catch (error) {
      setMessage(String(error));
    }
  };
  const run = () => {
    if (!input || busy || loadingInput) return;
    setBusy(true);
    setResult(undefined);
    worker.current ??= new Worker(new URL("../lib/network-model/worker.ts", import.meta.url), {
      type: "module",
    });
    worker.current.onmessage = (
      event: MessageEvent<Result & { kind: string; message: string }>,
    ) => {
      if (event.data.kind === "progress") setMessage(event.data.message);
      else {
        setBusy(false);
        if (event.data.kind === "result") {
          setResult(event.data);
          setMessage("Solve complete. Numerical optimum is not historical validation.");
        } else setMessage(event.data.message);
      }
    };
    worker.current.onerror = (event) => {
      setBusy(false);
      setMessage(`Worker failed: ${event.message}`);
      worker.current?.terminate();
      worker.current = null;
    };
    worker.current.postMessage({ input, patch });
  };
  return (
    <main className="mx-auto max-w-4xl space-y-6 px-5 py-8">
      <nav className="flex gap-5 text-sm">
        <Link to="/" className="underline">
          Map workbench
        </Link>
        <Link to="/docs" className="underline">
          Methods &amp; evidence
        </Link>
      </nav>
      <header>
        <p className="text-xs uppercase tracking-widest text-muted-foreground">
          Experimental · not validated
        </p>
        <h1 className="mt-3 text-3xl font-bold">Coupled network experiment</h1>
      </header>
      <p>
        Re-dispatch all zones together after adding transmission or storage. This lossless transport
        / optional PTDF model uses chronological availability, operating costs and demand—not
        observed price spreads.
      </p>
      <aside className="rounded border p-4 text-sm space-y-3">
        <p>
          <strong>Real-data technical benchmark available.</strong> The public 37-bus PyPSA archive
          contains 2013 weather/load, older existing fleet assumptions and hydro inflows. This is a
          one-week benchmark, not a validated 2025 investment estimate. Swedish cluster IDs are not
          bidding-zone labels.
        </p>
        <button
          disabled={busy || loadingInput || !ready}
          className="rounded border px-3 py-2"
          onClick={async () => {
            setLoadingInput(true);
            setResult(undefined);
            setMessage("Loading benchmark input…");
            try {
              const response = await fetch(publicAsset("research/network-benchmark/input.json"));
              if (!response.ok) throw new Error(`Dataset unavailable (${response.status})`);
              importModel(await response.json());
            } catch (error) {
              setMessage(String(error));
            } finally {
              setLoadingInput(false);
            }
          }}
        >
          Load real-data benchmark
        </button>
        <Link
          to="/docs/$slug"
          params={{ slug: "network-benchmark-comparison" }}
          className="ml-3 underline"
        >
          Results, speed and AC comparison
        </Link>
      </aside>
      <p className="text-sm">
        Import a schema-v1/v2 JSON input from your offline research pipeline. It stays in this
        browser. No weather processing, uploads or server are involved.{" "}
        <Link to="/docs/$slug" params={{ slug: "fast-network-model" }} className="underline">
          Input format, equations and limitations
        </Link>
        .
      </p>
      <label className="block">
        Model input (JSON, maximum 25 MiB)
        <input
          data-testid="network-input"
          className="mt-2 block w-full rounded border p-3"
          type="file"
          accept=".json,application/json"
          disabled={busy || loadingInput || !ready}
          onChange={async (event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            setLoadingInput(true);
            setResult(undefined);
            try {
              if (file.size > 25 * 1024 * 1024)
                throw new Error("Input exceeds 25 MiB browser import budget");
              importModel(JSON.parse(await file.text()));
            } catch (error) {
              setMessage(String(error));
            } finally {
              setLoadingInput(false);
            }
          }}
        />
      </label>
      {input && (
        <section className="space-y-4 rounded border p-4">
          <h2 className="text-xl font-semibold">{input.dataset_id}</h2>
          <p>
            {input.zones.length} zones · {input.timestamps.length} consecutive intervals ·{" "}
            {input.interval_hours} h each
          </p>
          <p className="break-all text-sm">
            Source: {input.provenance.source}
            <br />
            SHA-256: {input.provenance.source_sha256}
          </p>
          <ul className="list-disc pl-5 text-sm">
            {input.provenance.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
          <fieldset disabled={busy || loadingInput} className="space-y-3">
            <legend className="font-semibold">Transmission additions</legend>
            <div className="flex flex-wrap gap-3">
              <select
                aria-label="Interconnector"
                className="rounded border bg-background p-2"
                value={edge}
                onChange={(e) => setEdge(e.target.value)}
              >
                {input.edges.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.id} · {e.a} ↔ {e.b}
                  </option>
                ))}
              </select>
              <label>
                Additional MW{" "}
                <input
                  aria-label="Additional MW"
                  type="number"
                  min="0"
                  className="w-28 rounded border bg-background p-2"
                  value={mw}
                  onChange={(e) => setMw(Number(e.target.value))}
                />
              </label>
              <button
                className="rounded border px-3 py-2"
                disabled={!edge}
                onClick={() =>
                  edit({ ...patch, edge_additions_mw: { ...patch.edge_additions_mw, [edge]: mw } })
                }
              >
                Set capacity addition
              </button>
            </div>
            {Object.entries(patch.edge_additions_mw).map(([id, value]) => (
              <p key={id}>
                {id}: +{value} MW in both directions{" "}
                <button
                  className="underline"
                  onClick={() => {
                    const next = { ...patch.edge_additions_mw };
                    delete next[id];
                    edit({ ...patch, edge_additions_mw: next });
                  }}
                >
                  Remove
                </button>
              </p>
            ))}
            <legend className="font-semibold">Storage additions</legend>
            <div className="flex flex-wrap gap-3">
              <select
                aria-label="Storage zone"
                className="rounded border bg-background p-2"
                value={zone}
                onChange={(e) => setZone(e.target.value)}
              >
                {input.zones.map((z) => (
                  <option key={z}>{z}</option>
                ))}
              </select>
              <button
                className="rounded border px-3 py-2"
                onClick={() =>
                  edit({
                    ...patch,
                    storage: [
                      ...patch.storage,
                      {
                        id: crypto.randomUUID(),
                        zone,
                        power_mw: 100,
                        energy_mwh: 400,
                        initial_mwh: 0,
                        terminal_mwh: 0,
                        charge_efficiency: 0.95,
                        discharge_efficiency: 0.95,
                        throughput_cost_eur_mwh: 1,
                      },
                    ],
                  })
                }
              >
                Add 100 MW / 400 MWh battery
              </button>
            </div>
            <p className="text-sm text-muted-foreground">
              95% charge and discharge efficiency; €1/MWh throughput cost per charging/discharging
              leg; empty initial and terminal inventory.
            </p>
            {patch.storage.map((s) => (
              <p key={s.id}>
                {s.zone}: {s.power_mw} MW / {s.energy_mwh} MWh{" "}
                <button
                  className="underline"
                  onClick={() =>
                    edit({ ...patch, storage: patch.storage.filter((v) => v.id !== s.id) })
                  }
                >
                  Remove
                </button>
              </p>
            ))}
          </fieldset>
          <button
            data-testid="network-run"
            disabled={busy || loadingInput}
            className="rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
            onClick={run}
          >
            Evaluate network
          </button>
          {busy && (
            <button
              className="ml-3 underline"
              onClick={() => {
                worker.current?.terminate();
                worker.current = null;
                setBusy(false);
                setMessage("Cancelled. No result retained.");
              }}
            >
              Cancel
            </button>
          )}
        </section>
      )}
      <p role="status" className="break-words">
        {message}
      </p>
      {result && (
        <section data-testid="network-result" className="space-y-3 rounded border p-4">
          <h2 className="text-xl font-semibold">Experimental period result</h2>
          <button
            className="underline text-sm"
            onClick={() => {
              const url = URL.createObjectURL(
                new Blob(
                  [
                    JSON.stringify(
                      { result, input, patch, status: "experimental_not_validated" },
                      null,
                      2,
                    ),
                  ],
                  { type: "application/json" },
                ),
              );
              const anchor = document.createElement("a");
              anchor.href = url;
              anchor.download = "grid-conductor-network-experiment.json";
              anchor.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }}
          >
            Export input, interventions and results
          </button>
          <p>
            Operating cost reduction:{" "}
            <strong>
              €
              {result.comparison.period_benefit_eur.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              })}
            </strong>{" "}
            over the imported period.
          </p>
          <p>
            Baseline €{result.baseline.total_cost_eur.toLocaleString()} → intervention €
            {result.scenario.total_cost_eur.toLocaleString()}
          </p>
          <p>
            Dispatch emissions reduction:{" "}
            {result.comparison.avoided_co2_t === null
              ? "Unavailable: incomplete emission factors"
              : `${result.comparison.avoided_co2_t.toLocaleString()} t CO₂ (signed)`}
          </p>
          <p>
            Unserved energy: baseline {result.baseline.unserved_mwh.toFixed(4)} / scenario{" "}
            {result.scenario.unserved_mwh.toFixed(4)} MWh.
          </p>
          {result.comparison.scarcity_affected && (
            <p className="font-semibold">
              Scarcity affected: benefit includes assumed unserved-energy penalty. Do not interpret
              it as ordinary investment welfare.
            </p>
          )}
          {result.comparison.storage_relaxation_affected && (
            <p className="font-semibold">
              Simultaneous charge/discharge occurred. The continuous storage relaxation affects
              interpretation.
            </p>
          )}
          <p className="text-sm">
            Solve {Math.round(result.elapsed_ms)} ms; baseline{" "}
            {result.baseline_cached ? "cached" : "re-solved"}; maximum constraint violation{" "}
            {Math.max(
              result.baseline.max_constraint_violation,
              result.scenario.max_constraint_violation,
            ).toExponential(2)}
            . No annual extrapolation, investment NPV or within-zone locational claim.
          </p>
        </section>
      )}
    </main>
  );
}
