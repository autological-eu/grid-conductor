import { BatteryCharging, Cable, Fan, SlidersHorizontal, Sun, type LucideIcon } from "lucide-react";
import type { UnitType } from "./units";

/** crisp vector icon per unit type — used in the library and directly on the map */
export const UNIT_ICONS: Record<UnitType, LucideIcon> = {
  battery: BatteryCharging,
  solar: Sun,
  wind: Fan,
  line: Cable,
  demand_response: SlidersHorizontal,
};

export const unitIcon = (type: string): LucideIcon =>
  UNIT_ICONS[type as UnitType] ?? SlidersHorizontal;
