export type ZoneGroup = "EU" | "US";

export interface PilotZone {
  key: string;
  label: string;
  group: ZoneGroup;
}

export const PILOT_ZONES: PilotZone[] = [
  { key: "DK-DK1", label: "West Denmark", group: "EU" },
  { key: "DK-DK2", label: "East Denmark", group: "EU" },
  { key: "DE", label: "Germany", group: "EU" },
  { key: "FR", label: "France", group: "EU" },
  { key: "ES", label: "Spain", group: "EU" },
  { key: "NL", label: "Netherlands", group: "EU" },
  { key: "PL", label: "Poland", group: "EU" },
  { key: "SE-SE3", label: "South-Central Sweden", group: "EU" },
  { key: "NO-NO1", label: "Eastern Norway", group: "EU" },
  { key: "FI", label: "Finland", group: "EU" },
  { key: "US-TEX-ERCO", label: "ERCOT (Texas)", group: "US" },
  { key: "US-MIDA-PJM", label: "PJM", group: "US" },
  { key: "US-CAL-CISO", label: "CAISO (California)", group: "US" },
  { key: "US-MIDW-MISO", label: "MISO", group: "US" },
  { key: "US-SW-AZPS", label: "Arizona Public Service", group: "US" },
];

export const DEFAULT_ZONE = "DK-DK1";

export const ZONE_KEYS = PILOT_ZONES.map((z) => z.key);

export function zoneLabel(key: string): string {
  return PILOT_ZONES.find((z) => z.key === key)?.label ?? key;
}
