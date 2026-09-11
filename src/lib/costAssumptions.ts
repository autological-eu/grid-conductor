// Client-safe cost & performance assumptions used to size template scenarios.
// Update the numbers here to refresh what one million euros buys per technology.

export type TechnologyCost = {
  /** installed cost basis label shown in the UI, e.g. "€250 / kWh" */
  basis: string;
  /** annual capacity factor (or cycles/day for batteries, availability for lines) */
  factorLabel: string;
  /** expected annual energy per €1M, GWh — for display */
  annualGwhPerMeur: number | null;
};

export const COST_ASSUMPTIONS: Record<"battery" | "solar" | "wind" | "line", TechnologyCost> = {
  battery: {
    basis: "€250 / kWh (2 h system)",
    factorLabel: "1.5 cycles/day, 88% round-trip",
    annualGwhPerMeur: 2.2,
  },
  wind: {
    basis: "€1.3M / MW onshore",
    factorLabel: "27% capacity factor",
    annualGwhPerMeur: 1.8,
  },
  solar: {
    basis: "€0.7M / MW utility PV",
    factorLabel: "12% capacity factor",
    annualGwhPerMeur: 1.5,
  },
  line: {
    basis: "€0.4M per MW·100 km",
    factorLabel: "97% availability",
    annualGwhPerMeur: null,
  },
};

export const DEFAULT_TEMPLATE_BUDGET_MEUR = 1;

/** battery: €250 per kWh of energy capacity, 2 h duration */
export const BATTERY_EUR_PER_KWH = 250;
export const BATTERY_DURATION_H = 2;
/** wind / solar installed cost, MEUR per MW */
export const WIND_MEUR_PER_MW = 1.3;
export const SOLAR_MEUR_PER_MW = 0.7;
/** transmission: MEUR per MW of added capacity per 100 km of route length */
export const LINE_MEUR_PER_MW_PER_100KM = 0.4;

export type SizedUnit = {
  unit_type: "battery" | "solar" | "wind" | "line";
  params: Record<string, number>;
  capacity_label: string;
};

function round(v: number, d: number) {
  const f = 10 ** d;
  return Math.round(v * f) / f;
}

/** size a unit so its installed cost equals the budget */
export function sizeUnit(
  type: "battery" | "solar" | "wind" | "line",
  budgetMeur: number,
  distanceKm = 0,
): SizedUnit {
  switch (type) {
    case "battery": {
      const energyKwh = (budgetMeur * 1e6) / BATTERY_EUR_PER_KWH;
      const energyMwh = energyKwh / 1000;
      const powerMw = energyMwh / BATTERY_DURATION_H;
      return {
        unit_type: "battery",
        params: { power_mw: round(powerMw, 2), energy_mwh: round(energyMwh, 2), efficiency: 0.88 },
        capacity_label: `${round(powerMw, 2)} MW / ${round(energyMwh, 1)} MWh`,
      };
    }
    case "wind": {
      const mw = budgetMeur / WIND_MEUR_PER_MW;
      return {
        unit_type: "wind",
        params: { capacity_mw: round(mw, 3) },
        capacity_label: `${round(mw, 2)} MW`,
      };
    }
    case "solar": {
      const mw = budgetMeur / SOLAR_MEUR_PER_MW;
      return {
        unit_type: "solar",
        params: { capacity_mw: round(mw, 3) },
        capacity_label: `${round(mw, 2)} MW`,
      };
    }
    case "line": {
      const km = Math.max(distanceKm, 50);
      const mw = (budgetMeur / LINE_MEUR_PER_MW_PER_100KM) * (100 / km);
      return {
        unit_type: "line",
        params: { added_mw: round(mw, 1) },
        capacity_label: `+${round(mw, 1)} MW (~${Math.round(km)} km)`,
      };
    }
  }
}

/** great-circle distance in km between two lat/lon points */
export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number) {
  const r = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}
