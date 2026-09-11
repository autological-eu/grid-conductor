// Client-safe catalogue of scenario unit types.
export type UnitType = "battery" | "solar" | "wind" | "line" | "demand_response";

export type UnitDefinition = {
  type: UnitType;
  label: string;
  description: string;
  placement: "zone" | "border";
  defaults: Record<string, number>;
  fields: Array<{ key: string; label: string; unit: string; step?: number }>;
  defaultCapexMeur: number;
  defaultDeliveryMonths: number;
};

export const UNIT_LIBRARY: UnitDefinition[] = [
  {
    type: "battery",
    label: "Battery storage",
    description: "Shifts energy between hours inside one zone.",
    placement: "zone",
    defaults: { power_mw: 200, energy_mwh: 800, efficiency: 0.88 },
    fields: [
      { key: "power_mw", label: "Power", unit: "MW", step: 10 },
      { key: "energy_mwh", label: "Energy", unit: "MWh", step: 50 },
      { key: "efficiency", label: "Round-trip efficiency", unit: "0-1", step: 0.01 },
    ],
    defaultCapexMeur: 120,
    defaultDeliveryMonths: 24,
  },
  {
    type: "solar",
    label: "Solar farm",
    description: "Adds capacity following the zone's historical solar profile.",
    placement: "zone",
    defaults: { capacity_mw: 300 },
    fields: [{ key: "capacity_mw", label: "Capacity", unit: "MW", step: 25 }],
    defaultCapexMeur: 210,
    defaultDeliveryMonths: 18,
  },
  {
    type: "wind",
    label: "Wind farm",
    description: "Adds capacity following the zone's historical wind profile.",
    placement: "zone",
    defaults: { capacity_mw: 300 },
    fields: [{ key: "capacity_mw", label: "Capacity", unit: "MW", step: 25 }],
    defaultCapexMeur: 390,
    defaultDeliveryMonths: 36,
  },
  {
    type: "line",
    label: "Transmission line",
    description: "Raises the transfer limit on the target border.",
    placement: "border",
    defaults: { added_mw: 700 },
    fields: [{ key: "added_mw", label: "Added capacity", unit: "MW", step: 50 }],
    defaultCapexMeur: 650,
    defaultDeliveryMonths: 72,
  },
  {
    type: "demand_response",
    label: "Demand response",
    description: "Flexible load that can shift within the day.",
    placement: "zone",
    defaults: { power_mw: 150, shift_hours: 4 },
    fields: [
      { key: "power_mw", label: "Power", unit: "MW", step: 10 },
      { key: "shift_hours", label: "Shift window", unit: "h", step: 1 },
    ],
    defaultCapexMeur: 25,
    defaultDeliveryMonths: 12,
  },
];

export const unitDef = (type: string): UnitDefinition =>
  UNIT_LIBRARY.find((u) => u.type === type) ?? UNIT_LIBRARY[0]!;

/** currently dragged library unit (shared so the map can react during dragover) */
export const unitDrag: { current: UnitType | null } = { current: null };
