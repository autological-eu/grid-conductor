/**
 * Static ENTSO-E bidding-zone metadata for the Step-1 screening results
 * (`public/research/entsoe-fast-targets.json`).
 *
 * The Step-1 JSON publishes per-border opportunity (lost congestion rent) but
 * carries no coordinates and no carbon data. The Europe map needs a lat/lon per
 * zone and both metric columns (market + climate), so we supply them here:
 *   * lat/lon  – bidding-zone centroid (approx, schematic map accuracy)
 *   * name     – human label used on the map markers
 *   * carbon_g_per_kwh – national-average grid intensity approximation, used to
 *     estimate the climate side of each border from its released energy.
 *     This is an ORDER-OF-MAGNITUDE estimate only and is labelled "(est.)" in
 *     the UI; it is never to be mistaken for screened CO2 data.
 */

export type EntsoeZoneMeta = {
  code: string;
  name: string;
  country_code: string;
  lat: number;
  lon: number;
  /** approximate national-average grid carbon intensity (g CO2/kWh) */
  carbon_g_per_kwh: number;
};

export const ENTSOE_ZONES: Record<string, EntsoeZoneMeta> = {
  AT: {
    code: "AT",
    name: "Austria",
    country_code: "AT",
    lat: 47.5,
    lon: 14.4,
    carbon_g_per_kwh: 150,
  },
  AL: {
    code: "AL",
    name: "Albania",
    country_code: "AL",
    lat: 41.15,
    lon: 20.17,
    carbon_g_per_kwh: 50,
  },
  BE: {
    code: "BE",
    name: "Belgium",
    country_code: "BE",
    lat: 50.6,
    lon: 4.7,
    carbon_g_per_kwh: 240,
  },
  BG: {
    code: "BG",
    name: "Bulgaria",
    country_code: "BG",
    lat: 42.7,
    lon: 25.4,
    carbon_g_per_kwh: 460,
  },
  CZ: {
    code: "CZ",
    name: "Czechia",
    country_code: "CZ",
    lat: 49.8,
    lon: 15.5,
    carbon_g_per_kwh: 470,
  },
  CH: {
    code: "CH",
    name: "Switzerland",
    country_code: "CH",
    lat: 46.79,
    lon: 8.23,
    carbon_g_per_kwh: 30,
  },
  "DE-LU": {
    code: "DE-LU",
    name: "Germany / Luxembourg",
    country_code: "DE",
    lat: 51.1,
    lon: 10.4,
    carbon_g_per_kwh: 360,
  },
  DK1: {
    code: "DK1",
    name: "Denmark (West)",
    country_code: "DK",
    lat: 56.1,
    lon: 8.9,
    carbon_g_per_kwh: 180,
  },
  DK2: {
    code: "DK2",
    name: "Denmark (East)",
    country_code: "DK",
    lat: 55.7,
    lon: 12.2,
    carbon_g_per_kwh: 90,
  },
  EE: {
    code: "EE",
    name: "Estonia",
    country_code: "EE",
    lat: 58.9,
    lon: 25.5,
    carbon_g_per_kwh: 620,
  },
  ES: {
    code: "ES",
    name: "Spain",
    country_code: "ES",
    lat: 40.4,
    lon: -3.7,
    carbon_g_per_kwh: 240,
  },
  FI: {
    code: "FI",
    name: "Finland",
    country_code: "FI",
    lat: 63.9,
    lon: 25.5,
    carbon_g_per_kwh: 85,
  },
  FR: { code: "FR", name: "France", country_code: "FR", lat: 46.6, lon: 2.4, carbon_g_per_kwh: 60 },
  GR: {
    code: "GR",
    name: "Greece",
    country_code: "GR",
    lat: 39.1,
    lon: 22.0,
    carbon_g_per_kwh: 500,
  },
  HR: {
    code: "HR",
    name: "Croatia",
    country_code: "HR",
    lat: 45.4,
    lon: 15.8,
    carbon_g_per_kwh: 270,
  },
  HU: {
    code: "HU",
    name: "Hungary",
    country_code: "HU",
    lat: 47.2,
    lon: 19.5,
    carbon_g_per_kwh: 340,
  },
  "IT-CNOR": {
    code: "IT-CNOR",
    name: "Italy North-Central",
    country_code: "IT",
    lat: 44.9,
    lon: 11.0,
    carbon_g_per_kwh: 410,
  },
  "IT-CSUD": {
    code: "IT-CSUD",
    name: "Italy Central-South",
    country_code: "IT",
    lat: 42.3,
    lon: 13.0,
    carbon_g_per_kwh: 460,
  },
  "IT-North": {
    code: "IT-North",
    name: "Italy North",
    country_code: "IT",
    lat: 45.5,
    lon: 9.0,
    carbon_g_per_kwh: 320,
  },
  "IT-SARD": {
    code: "IT-SARD",
    name: "Sardinia",
    country_code: "IT",
    lat: 40.0,
    lon: 9.1,
    carbon_g_per_kwh: 460,
  },
  "IT-SICI": {
    code: "IT-SICI",
    name: "Sicily",
    country_code: "IT",
    lat: 37.6,
    lon: 14.1,
    carbon_g_per_kwh: 500,
  },
  "IT-SUD": {
    code: "IT-SUD",
    name: "Italy South",
    country_code: "IT",
    lat: 40.7,
    lon: 15.5,
    carbon_g_per_kwh: 470,
  },
  LT: {
    code: "LT",
    name: "Lithuania",
    country_code: "LT",
    lat: 55.3,
    lon: 23.9,
    carbon_g_per_kwh: 420,
  },
  LV: {
    code: "LV",
    name: "Latvia",
    country_code: "LV",
    lat: 56.8,
    lon: 24.7,
    carbon_g_per_kwh: 200,
  },
  MK: {
    code: "MK",
    name: "North Macedonia",
    country_code: "MK",
    lat: 41.6,
    lon: 21.74,
    carbon_g_per_kwh: 650,
  },
  NL: {
    code: "NL",
    name: "Netherlands",
    country_code: "NL",
    lat: 52.2,
    lon: 5.4,
    carbon_g_per_kwh: 360,
  },
  NO1: {
    code: "NO1",
    name: "Norway (Oslo)",
    country_code: "NO",
    lat: 60.0,
    lon: 10.5,
    carbon_g_per_kwh: 10,
  },
  NO2: {
    code: "NO2",
    name: "Norway (Kristiansand)",
    country_code: "NO",
    lat: 58.7,
    lon: 6.9,
    carbon_g_per_kwh: 10,
  },
  NO3: {
    code: "NO3",
    name: "Norway (Trondheim)",
    country_code: "NO",
    lat: 63.4,
    lon: 10.4,
    carbon_g_per_kwh: 10,
  },
  NO4: {
    code: "NO4",
    name: "Norway (Tromsø)",
    country_code: "NO",
    lat: 68.7,
    lon: 16.0,
    carbon_g_per_kwh: 10,
  },
  PL: {
    code: "PL",
    name: "Poland",
    country_code: "PL",
    lat: 52.1,
    lon: 19.5,
    carbon_g_per_kwh: 660,
  },
  PT: {
    code: "PT",
    name: "Portugal",
    country_code: "PT",
    lat: 39.6,
    lon: -8.0,
    carbon_g_per_kwh: 180,
  },
  RO: {
    code: "RO",
    name: "Romania",
    country_code: "RO",
    lat: 45.9,
    lon: 25.1,
    carbon_g_per_kwh: 400,
  },
  RS: {
    code: "RS",
    name: "Serbia",
    country_code: "RS",
    lat: 44.0,
    lon: 20.9,
    carbon_g_per_kwh: 700,
  },
  SE1: {
    code: "SE1",
    name: "Sweden Luleå",
    country_code: "SE",
    lat: 66.2,
    lon: 20.8,
    carbon_g_per_kwh: 30,
  },
  SE2: {
    code: "SE2",
    name: "Sweden Sundsvall",
    country_code: "SE",
    lat: 64.0,
    lon: 19.5,
    carbon_g_per_kwh: 35,
  },
  SE3: {
    code: "SE3",
    name: "Sweden Stockholm",
    country_code: "SE",
    lat: 60.6,
    lon: 15.8,
    carbon_g_per_kwh: 40,
  },
  SE4: {
    code: "SE4",
    name: "Sweden Malmö",
    country_code: "SE",
    lat: 56.5,
    lon: 13.7,
    carbon_g_per_kwh: 60,
  },
  SI: {
    code: "SI",
    name: "Slovenia",
    country_code: "SI",
    lat: 46.1,
    lon: 15.0,
    carbon_g_per_kwh: 200,
  },
  SK: {
    code: "SK",
    name: "Slovakia",
    country_code: "SK",
    lat: 48.7,
    lon: 19.5,
    carbon_g_per_kwh: 310,
  },
};

export function entsoeZoneMeta(code: string): EntsoeZoneMeta {
  return (
    ENTSOE_ZONES[code] ?? {
      code,
      name: code,
      country_code: code.split("-")[0] ?? code,
      lat: 0,
      lon: 0,
      carbon_g_per_kwh: 200,
    }
  );
}
