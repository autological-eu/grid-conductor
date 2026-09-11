import { createServerFn } from "@tanstack/react-start";

import { analysisWindow, SIGNALS, type Signal } from "./window";

const CHUNK_DAYS = 10;
const LOCK_NAME = "historical-import";
const LOCK_MINUTES = 5;

type Row = Record<string, unknown>;

function iso(d: Date): string {
  return d.toISOString().slice(0, 19) + "Z";
}

/** Create (or top up) the import plan: one job per zone and signal. */
export const planImport = createServerFn({ method: "POST" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { start, end } = analysisWindow();

  const { data: zones, error } = await supabaseAdmin.from("zones").select("code");
  if (error) throw new Error(error.message);

  const jobs = (zones ?? []).flatMap((z) =>
    SIGNALS.map((signal) => ({
      zone_code: z.code,
      signal,
      range_start: start.toISOString(),
      range_end: end.toISOString(),
      cursor_ts: start.toISOString(),
      status: "pending",
    })),
  );

  const { error: upErr } = await supabaseAdmin
    .from("import_jobs")
    .upsert(jobs, { onConflict: "zone_code,signal,range_start,range_end", ignoreDuplicates: true });
  if (upErr) throw new Error(upErr.message);

  return { jobs: jobs.length, start: start.toISOString(), end: end.toISOString() };
});

export const getImportProgress = createServerFn({ method: "GET" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { data, error } = await supabaseAdmin
    .from("import_jobs")
    .select("zone_code, signal, status, cursor_ts, range_start, range_end, rows_imported, last_error");
  if (error) throw new Error(error.message);

  const jobs = data ?? [];
  const total = jobs.length;
  const done = jobs.filter((j) => j.status === "done").length;
  const failed = jobs.filter((j) => j.status === "error").length;
  const rows = jobs.reduce((s, j) => s + (j.rows_imported ?? 0), 0);

  const fraction = total
    ? jobs.reduce((s, j) => {
        const span =
          new Date(j.range_end).getTime() - new Date(j.range_start).getTime();
        const got = new Date(j.cursor_ts).getTime() - new Date(j.range_start).getTime();
        return s + (span > 0 ? Math.min(1, Math.max(0, got / span)) : 0);
      }, 0) / total
    : 0;

  const { data: lock } = await supabaseAdmin
    .from("job_locks")
    .select("expires_at, paused, pause_reason")
    .eq("name", LOCK_NAME)
    .maybeSingle();

  const zonesComplete = new Set(
    jobs.filter((j) => j.status === "done").map((j) => j.zone_code),
  ).size;

  return {
    total,
    done,
    failed,
    rows,
    fraction,
    zonesComplete,
    running: !!lock && new Date(lock.expires_at).getTime() > Date.now(),
    paused: !!lock?.paused,
    pauseReason: lock?.pause_reason ?? null,
    errors: jobs
      .filter((j) => j.last_error)
      .slice(0, 5)
      .map((j) => `${j.zone_code}/${j.signal}: ${j.last_error}`),
  };
});

/**
 * Process a bounded number of 10-day chunks. Single-flight via a lease row;
 * every chunk is idempotent (upsert) and the cursor advances only on success.
 */
export const runImportBatch = createServerFn({ method: "POST" })
  .inputValidator((data: { chunks?: number } | undefined) => data ?? {})
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { fetchSignalRange, EmapsError } = await import("./emaps.server");
    const budget = Math.min(Math.max(data.chunks ?? 6, 1), 12);

    const { data: lock } = await supabaseAdmin
      .from("job_locks")
      .select("expires_at, paused, pause_reason")
      .eq("name", LOCK_NAME)
      .maybeSingle();

    if (lock?.paused) return { skipped: "paused" as const, reason: lock.pause_reason };
    if (lock && new Date(lock.expires_at).getTime() > Date.now())
      return { skipped: "running" as const };

    const release = async (paused = false, reason: string | null = null) => {
      await supabaseAdmin.from("job_locks").upsert({
        name: LOCK_NAME,
        expires_at: new Date().toISOString(),
        paused,
        pause_reason: reason,
        updated_at: new Date().toISOString(),
      });
    };

    await supabaseAdmin.from("job_locks").upsert({
      name: LOCK_NAME,
      expires_at: new Date(Date.now() + LOCK_MINUTES * 60_000).toISOString(),
      paused: false,
      pause_reason: null,
      updated_at: new Date().toISOString(),
    });

    let processed = 0;
    let imported = 0;

    try {
      const { data: jobs } = await supabaseAdmin
        .from("import_jobs")
        .select("*")
        .in("status", ["pending", "running"])
        .order("zone_code")
        .limit(budget);

      if (!jobs?.length) {
        await release();
        return { processed: 0, imported: 0, complete: true };
      }

      for (const job of jobs) {
        const cursor = new Date(job.cursor_ts);
        const rangeEnd = new Date(job.range_end);
        if (cursor >= rangeEnd) {
          await supabaseAdmin
            .from("import_jobs")
            .update({ status: "done" })
            .eq("id", job.id);
          continue;
        }
        const chunkEnd = new Date(
          Math.min(
            cursor.getTime() + CHUNK_DAYS * 86_400_000,
            rangeEnd.getTime(),
          ),
        );

        try {
          const points = await fetchSignalRange(
            job.signal as Signal,
            job.zone_code,
            iso(cursor),
            iso(chunkEnd),
          );
          const written = await writePoints(
            supabaseAdmin as unknown as Parameters<typeof writePoints>[0],
            job.signal as Signal,
            job.zone_code,
            points,
          );
          imported += written;
          processed += 1;

          const finished = chunkEnd >= rangeEnd;
          await supabaseAdmin
            .from("import_jobs")
            .update({
              cursor_ts: chunkEnd.toISOString(),
              status: finished ? "done" : "running",
              rows_imported: (job.rows_imported ?? 0) + written,
              last_error: null,
            })
            .eq("id", job.id);
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          const status = err instanceof EmapsError ? err.status : 0;

          // 401 = zone/signal not in plan: skip this job entirely rather than looping.
          const terminal = status === 401 || status === 400;
          await supabaseAdmin
            .from("import_jobs")
            .update({ status: terminal ? "error" : "pending", last_error: msg })
            .eq("id", job.id);

          if (status === 429 || status === 402) {
            await release(status === 402, msg);
            return { processed, imported, complete: false, throttled: true };
          }
        }
      }

      const { count } = await supabaseAdmin
        .from("import_jobs")
        .select("id", { count: "exact", head: true })
        .in("status", ["pending", "running"]);

      await release();
      return { processed, imported, complete: (count ?? 0) === 0 };
    } catch (err) {
      await release();
      throw err;
    }
  });

async function writePoints(
  db: {
    from: (t: string) => {
      upsert: (rows: Row[], opts: { onConflict: string }) => PromiseLike<{ error: { message: string } | null }>;
    };
  },
  signal: Signal,
  zone: string,
  points: Row[],
): Promise<number> {
  if (!points.length) return 0;

  if (signal === "flows") {
    const rows: Row[] = [];
    for (const p of points) {
      const ts = p["datetime"] as string | undefined;
      if (!ts) continue;
      const imports = (p["import"] ?? {}) as Record<string, number>;
      const exports = (p["export"] ?? {}) as Record<string, number>;
      const neighbours = new Set([...Object.keys(imports), ...Object.keys(exports)]);
      for (const n of neighbours) {
        const net = (exports[n] ?? 0) - (imports[n] ?? 0); // positive: zone -> n
        const a = zone < n ? zone : n;
        const b = zone < n ? n : zone;
        rows.push({
          zone_a: a,
          zone_b: b,
          ts,
          flow_mw: zone === a ? net : -net,
        });
      }
    }
    return upsertChunks(db, "border_flow_hourly", rows, "zone_a,zone_b,ts");
  }

  const column =
    signal === "price"
      ? "price_eur_mwh"
      : signal === "carbon"
        ? "carbon_intensity"
        : signal === "load"
          ? "load_mw"
          : "mix";

  const rows: Row[] = [];
  for (const p of points) {
    const ts = p["datetime"] as string | undefined;
    if (!ts) continue;
    let value: unknown;
    if (signal === "mix") value = p["mix"] ?? null;
    else if (signal === "carbon") value = p["carbonIntensity"] ?? p["value"] ?? null;
    else value = p["value"] ?? null;
    if (value === null || value === undefined) continue;
    rows.push({ zone_code: zone, ts, [column]: value });
  }
  return upsertChunks(db, "zone_hourly", rows, "zone_code,ts");
}

async function upsertChunks(
  db: {
    from: (t: string) => {
      upsert: (rows: Row[], opts: { onConflict: string }) => PromiseLike<{ error: { message: string } | null }>;
    };
  },
  table: string,
  rows: Row[],
  onConflict: string,
): Promise<number> {
  const SIZE = 500;
  for (let i = 0; i < rows.length; i += SIZE) {
    const { error } = await db.from(table).upsert(rows.slice(i, i + SIZE), { onConflict });
    if (error) throw new Error(error.message);
  }
  return rows.length;
}
