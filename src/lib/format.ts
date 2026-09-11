export const fmtL = (v: number | null | undefined, d = 2) =>
  v == null || !Number.isFinite(v) ? "—" : v.toFixed(d);

export const fmtPct = (v: number | null | undefined, d = 0) =>
  v == null || !Number.isFinite(v) ? "—" : (v * 100).toFixed(d);

export const fmtNum = (v: number | null | undefined, d = 0) =>
  v == null || !Number.isFinite(v) ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d });

export const localTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

export const localHour = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

export const utcLabel = (iso: string) => `${new Date(iso).toISOString().slice(0, 16).replace("T", " ")} UTC`;
