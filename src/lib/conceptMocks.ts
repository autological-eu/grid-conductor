/**
 * WaterTrace — MOCK data for the advanced concept signals (X1–X6).
 * Everything here is SYNTHETIC and deterministic (seeded). It is NOT WRI Aqueduct, AiDASH, Copernicus
 * or any partner's data. Every screen using it must show the "Concept · mock data" badge.
 */

export function rng(seed: string) {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) { h = Math.imul(h ^ seed.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
  let a = h >>> 0;
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

const round = (v: number, d = 2) => Math.round(v * 10 ** d) / 10 ** d;

/** X1 — mock generation-weighted basin water stress (0–5, Aqueduct-style scale) per zone. */
export const MOCK_BASIN_STRESS: Record<string, number> = {
  "DK-DK1": 1.1, "DK-DK2": 1.4, DE: 1.9, FR: 2.2, ES: 3.9, NL: 1.6, PL: 2.6, "SE-SE3": 0.5, "NO-NO1": 0.3, FI: 0.4,
  "US-TEX-ERCO": 3.4, "US-MIDA-PJM": 1.7, "US-CAL-CISO": 4.1, "US-MIDW-MISO": 1.5, "US-SW-AZPS": 4.7,
};

export const stressCategory = (s: number) =>
  s < 1 ? "Low" : s < 2 ? "Low–medium" : s < 3 ? "Medium–high" : s < 4 ? "High" : "Extremely high";

/** Stress multiplier: 1.0 at medium stress (2.5); ~0.2 in low-stress, ~2.5 in extremely high stress basins. */
export const stressMultiplier = (s: number) => round(0.2 + (s / 5) ** 1.5 * 2.6, 2);

export function x1StressWeighted(zone: string, w1LperKWh: number) {
  const s = MOCK_BASIN_STRESS[zone] ?? 2.5;
  return { zone, basinStress: s, category: stressCategory(s), multiplier: stressMultiplier(s), stressWeighted_Leq_per_kWh: round(w1LperKWh * stressMultiplier(s), 3) };
}

/** X2 — mock satellite cooling classification of thermal units (AiDASH-style pipeline concept). */
export type Cooling = "tower" | "once_through" | "once_through_sea" | "pond" | "dry";

export function x2Plants(zone: string, n = 8) {
  const r = rng("x2" + zone);
  const hasNuclear = ["FR", "ES", "SE-SE3", "FI", "NL", "BE", "GB", "CH", "CZ"].includes(zone) || zone.startsWith("US-");
  const fuels = (hasNuclear ? ["nuclear", "coal", "gas", "gas", "biomass"] : ["coal", "gas", "gas", "biomass"]) as readonly ("nuclear" | "coal" | "gas" | "biomass")[];
  const techs: Cooling[] = ["tower", "once_through", "once_through_sea", "dry", "pond"];
  return Array.from({ length: n }, (_, i) => {
    const fuel = fuels[Math.floor(r() * fuels.length)];
    const sat = techs[Math.floor(r() * (fuel === "gas" ? 4 : 3))];
    const registryKnown = r() < 0.45;
    return {
      id: `${zone}-U${String(i + 1).padStart(2, "0")}`, // generic IDs — never real plant names
      fuel, capacityMW: Math.round(200 + r() * (fuel === "nuclear" ? 1400 : 700)),
      registryCooling: registryKnown ? sat : "unknown",
      satelliteCooling: sat,
      confidence: round(0.78 + r() * 0.2, 2),
      evidence: sat === "tower" ? "cooling-tower shadows / plume" : sat === "dry" ? "air-cooled condenser fan arrays" : sat === "once_through_sea" ? "coastal intake + outfall" : sat === "pond" ? "cooling reservoir" : "river intake + outfall structures",
    };
  });
}

export function x2ConfidenceUplift(zone: string) {
  const r = rng("x2c" + zone);
  const before = round(0.35 + r() * 0.2, 2), after = round(0.82 + r() * 0.12, 2);
  const w1Delta = round((r() - 0.5) * 0.3, 2); // -15% .. +15% correction of W1
  return { zone, profileConfidenceBefore: before, profileConfidenceAfter: after, w1Correction: w1Delta };
}

/** X3 — mock wet-bulb temperature and evaporation uplift for tower-cooled generation. */
export function x3Weather(zone: string, hours = 72, heatwave = false) {
  const r = rng("x3" + zone + heatwave);
  const base = heatwave ? 23 : 14;
  return Array.from({ length: hours }, (_, h) => {
    const twb = round(base + 5 * Math.sin(((h % 24) - 9) / 24 * 2 * Math.PI) + (r() - 0.5) * 2, 1);
    const uplift = round(Math.max(-0.1, 0.012 * (twb - 15)), 3); // +1.2 % per °C wet-bulb above 15 °C (mock coefficient)
    return { hour: h, wetBulbC: twb, towerEvaporationUplift: uplift };
  });
}

/** X4 — mock refined reservoir-evaporation factors (L/kWh) vs the global US-derived default (17.0). */
export const X4_DEFAULT_HYDRO_L_PER_KWH = 17.0;
export const MOCK_HYDRO_REFINED: Record<string, number> = {
  "NO-NO1": 0.9, "SE-SE3": 1.3, FI: 1.6, FR: 4.2, ES: 11.5, DE: 2.8, PL: 3.1, "US-CAL-CISO": 13.8, "US-SW-AZPS": 21.0, "US-MIDW-MISO": 5.5, "US-TEX-ERCO": 18.2, "US-MIDA-PJM": 4.0,
};

/** X5 — mock river temperature vs regulatory limit and thermal capacity at risk. */
export function x5Derating(zone: string, days = 14) {
  const r = rng("x5" + zone);
  const limit = 27.0;
  return Array.from({ length: days }, (_, d) => {
    const riverC = round(22 + d * 0.35 + (r() - 0.3) * 2.2, 1);
    const excess = Math.max(0, riverC - (limit - 1.5));
    const capacityAtRiskMW = Math.round(excess * (800 + r() * 900));
    const spikeProbability = round(Math.min(0.95, excess * 0.22 + r() * 0.05), 2);
    return { day: d, riverTempC: riverC, limitC: limit, capacityAtRiskMW, priceSpikeProbability: spikeProbability };
  });
}

/** X6 — mock facility telemetry (measured WUE/PUE, hourly) to compare against modelled defaults. */
export function x6Telemetry(hours = 72) {
  const r = rng("x6");
  return Array.from({ length: hours }, (_, h) => {
    const outdoorC = 12 + 9 * Math.sin(((h % 24) - 9) / 24 * 2 * Math.PI) + (r() - 0.5) * 2;
    const wue = round(Math.max(0.05, 0.25 + 0.09 * Math.max(0, outdoorC - 12) + (r() - 0.5) * 0.1), 2);
    const pue = round(1.18 + 0.012 * Math.max(0, outdoorC - 15) + (r() - 0.5) * 0.02, 3);
    return { hour: h, outdoorC: round(outdoorC, 1), itLoadKW: Math.round(4800 + (r() - 0.5) * 400), measuredWUE: wue, measuredPUE: pue };
  });
}
