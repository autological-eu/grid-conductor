import loadHighs from "highs";
import wasmUrl from "highs/runtime?url";
import { parseNetworkInput } from "./schema";
import {
  applyIntervention,
  compareDispatch,
  dispatchNetwork,
  type Intervention,
  type DispatchResult,
  NetworkSolverSession,
} from "./solver";

let baseline: { fingerprint: string; result: DispatchResult } | undefined;
let session: NetworkSolverSession | undefined;
const runtime = loadHighs({ locateFile: () => wasmUrl });
// One worker per request stream; UI prevents concurrent jobs and terminates on cancel.
self.onmessage = async (event: MessageEvent<{ input: unknown; patch: Intervention }>) => {
  try {
    const data = parseNetworkInput(event.data.input);
    const patched = applyIntervention(data, event.data.patch);
    const fingerprint = JSON.stringify(data);
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(fingerprint));
    const input_sha256 = Array.from(new Uint8Array(digest), (b) =>
      b.toString(16).padStart(2, "0"),
    ).join("");
    const highs = await runtime;
    session ??= new NetworkSolverSession(highs);
    const start = performance.now();
    const cached = baseline?.fingerprint === fingerprint;
    self.postMessage({
      kind: "progress",
      message: cached ? "Reusing identical baseline" : "Solving chronological baseline",
    });
    if (!cached) baseline = { fingerprint, result: dispatchNetwork(highs, data, session) };
    self.postMessage({ kind: "progress", message: "Solving intervention across the network" });
    const scenario = dispatchNetwork(highs, patched, session);
    const base = baseline!.result;
    self.postMessage({
      kind: "result",
      input_sha256,
      model_version: "linked-dispatch-browser-v1",
      baseline: base,
      scenario,
      comparison: compareDispatch(base, scenario),
      elapsed_ms: performance.now() - start,
      baseline_cached: cached,
    });
  } catch (error) {
    self.postMessage({
      kind: "error",
      message: error instanceof Error ? error.message : String(error),
    });
  }
};
