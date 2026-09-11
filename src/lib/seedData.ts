// Seed data for WaterTrace — generated from water_factors.json and zone_profiles.json.
// Factors: Macknick et al. 2012 (NREL). Zone cooling profiles are ILLUSTRATIVE until calibrated.

export const WATER_FACTORS = {
  "unit": "L/MWh",
  "source": "Macknick, Newmark, Heath & Hallett (2012), NREL/TP-6A20-50900, operational medians; converted from gal/MWh",
  "notes": {
    "gas": "Natural gas combined-cycle factors used for Electricity Maps 'gas' (dominant technology). Open-cycle peakers use ~0.",
    "oil": "Natural gas steam-turbine factors used as proxy for oil-fired steam plants.",
    "geothermal": "Flash/tower median. Binary plants with wet cooling can be ~13,600 L/MWh (low confidence).",
    "solar": "Utility-scale PV panel washing. Rooftop PV likely lower.",
    "hydro": "Gross reservoir evaporation, US-derived, allocation to power contested. Excluded by default; shown only when 'include hydro evaporation' is on.",
    "storage": "Hydro storage and battery discharge = 0 (water already counted when the stored energy was generated).",
    "unknown": "Uses the zone's thermal-average factor (generation-weighted over coal, gas, oil, biomass, nuclear in the same hour), else gas.",
    "once_through_sea": "Seawater once-through cooling counts as 0 for FRESHWATER metrics and uses once-through factors for TOTAL-water metrics."
  },
  "thermal": {
    "nuclear": {
      "tower": {
        "consumption": { "median": 2544, "min": 2199, "max": 3199 },
        "withdrawal": { "median": 4168, "min": 3028, "max": 9842 }
      },
      "once_through": {
        "consumption": { "median": 1018, "min": 379, "max": 1514 },
        "withdrawal": { "median": 167883, "min": 94635, "max": 227125 }
      },
      "pond": {
        "consumption": { "median": 2309, "min": 2120, "max": 2725 },
        "withdrawal": { "median": 26687, "min": 1893, "max": 49210 }
      }
    },
    "coal": {
      "tower": {
        "consumption": { "median": 2601, "min": 1817, "max": 4164 },
        "withdrawal": { "median": 3804, "min": 1893, "max": 4542 }
      },
      "once_through": {
        "consumption": { "median": 946, "min": 379, "max": 1200 },
        "withdrawal": { "median": 137600, "min": 75708, "max": 189270 }
      },
      "pond": {
        "consumption": { "median": 2063, "min": 1136, "max": 2650 },
        "withdrawal": { "median": 46277, "min": 1136, "max": 90850 }
      }
    },
    "gas": {
      "tower": {
        "consumption": { "median": 750, "min": 492, "max": 1136 },
        "withdrawal": { "median": 958, "min": 568, "max": 1071 }
      },
      "once_through": {
        "consumption": { "median": 379, "min": 76, "max": 379 },
        "withdrawal": { "median": 43078, "min": 28391, "max": 75708 }
      },
      "pond": {
        "consumption": { "median": 908, "min": 908, "max": 908 },
        "withdrawal": { "median": 22523, "min": 22523, "max": 22523 }
      },
      "dry": {
        "consumption": { "median": 8, "min": 0, "max": 15 },
        "withdrawal": { "median": 8, "min": 0, "max": 15 }
      }
    },
    "oil": {
      "tower": {
        "consumption": { "median": 3127, "min": 2506, "max": 4429 },
        "withdrawal": { "median": 4554, "min": 3596, "max": 5527 }
      },
      "once_through": {
        "consumption": { "median": 908, "min": 360, "max": 1102 },
        "withdrawal": { "median": 132489, "min": 37854, "max": 227125 }
      }
    },
    "biomass": {
      "tower": {
        "consumption": { "median": 2093, "min": 1817, "max": 3653 },
        "withdrawal": { "median": 3324, "min": 1893, "max": 5527 }
      },
      "once_through": {
        "consumption": { "median": 1136, "min": 1136, "max": 1136 },
        "withdrawal": { "median": 132489, "min": 75708, "max": 189270 }
      },
      "pond": {
        "consumption": { "median": 1476, "min": 1136, "max": 1817 },
        "withdrawal": { "median": 1703, "min": 1136, "max": 2271 }
      }
    }
  },
  "single": {
    "geothermal": {
      "consumption": { "median": 38, "min": 19, "max": 72 },
      "withdrawal": { "median": 38, "min": 19, "max": 72 }
    },
    "solar": {
      "consumption": { "median": 98, "min": 0, "max": 125 },
      "withdrawal": { "median": 98, "min": 0, "max": 125 }
    },
    "wind": {
      "consumption": { "median": 0, "min": 0, "max": 4 },
      "withdrawal": { "median": 0, "min": 0, "max": 4 }
    },
    "hydro": {
      "consumption": { "median": 17000, "min": 5394, "max": 68137 },
      "withdrawal": { "median": 0, "min": 0, "max": 0 },
      "withdrawal_note": "In-stream use; not counted as withdrawal."
    }
  }
};

export const ZONE_PROFILES = {
  "status": "ILLUSTRATIVE - replace with calibrated shares before any external use",
  "calibration": {
    "US": "EIA Thermoelectric cooling water data (Cooling_Boiler_Generator_Data_Summary_<year>.xlsx) + EIA-860 Schedule 6; aggregate generator cooling type x fuel by Balancing Authority, weighted by net generation.",
    "EU": "Plant registries (JRC-PPDB-OPEN, Global Energy Monitor Global Integrated Power Tracker) + cooling type (satellite, see concept X2)."
  },
  "categories": [
    "tower",
    "once_through",
    "once_through_sea",
    "pond",
    "dry"
  ],
  "default": {
    "tower": 0.6,
    "once_through": 0.3,
    "once_through_sea": 0.1
  },
  "zones": [
    {
      "key": "DK-DK1",
      "name": "West Denmark",
      "region": "EU",
      "pilot": true,
      "lat": 56.2,
      "lon": 9.0,
      "cooling": {
        "coal": { "once_through_sea": 0.85, "tower": 0.15 },
        "gas": { "once_through_sea": 0.6, "tower": 0.2, "dry": 0.2 },
        "biomass": { "once_through_sea": 0.8, "tower": 0.2 },
        "oil": { "once_through_sea": 1.0 }
      }
    },
    {
      "key": "DK-DK2",
      "name": "East Denmark",
      "region": "EU",
      "pilot": true,
      "lat": 55.6,
      "lon": 12.1,
      "cooling": {
        "coal": { "once_through_sea": 0.85, "tower": 0.15 },
        "gas": { "once_through_sea": 0.6, "tower": 0.2, "dry": 0.2 },
        "biomass": { "once_through_sea": 0.8, "tower": 0.2 },
        "oil": { "once_through_sea": 1.0 }
      }
    },
    {
      "key": "DE",
      "name": "Germany",
      "region": "EU",
      "pilot": true,
      "lat": 51.2,
      "lon": 10.4,
      "cooling": {
        "coal": { "tower": 0.75, "once_through": 0.2, "once_through_sea": 0.05 },
        "gas": { "tower": 0.6, "once_through": 0.3, "dry": 0.1 },
        "biomass": { "tower": 0.6, "once_through": 0.4 },
        "oil": { "tower": 0.5, "once_through": 0.5 },
        "nuclear": { "tower": 1.0 }
      }
    },
    {
      "key": "FR",
      "name": "France",
      "region": "EU",
      "pilot": true,
      "lat": 46.6,
      "lon": 2.4,
      "cooling": {
        "nuclear": { "tower": 0.5, "once_through": 0.15, "once_through_sea": 0.35 },
        "gas": { "tower": 0.6, "once_through": 0.2, "once_through_sea": 0.2 },
        "coal": { "tower": 0.5, "once_through_sea": 0.5 },
        "biomass": { "tower": 0.7, "once_through": 0.3 },
        "oil": { "tower": 0.5, "once_through_sea": 0.5 }
      }
    },
    {
      "key": "ES",
      "name": "Spain",
      "region": "EU",
      "pilot": true,
      "lat": 40.3,
      "lon": -3.7,
      "cooling": {
        "nuclear": { "tower": 0.5, "once_through": 0.3, "once_through_sea": 0.2 },
        "gas": { "tower": 0.5, "once_through_sea": 0.4, "dry": 0.1 },
        "coal": { "tower": 0.5, "once_through_sea": 0.5 },
        "biomass": { "tower": 1.0 }
      }
    },
    {
      "key": "NL",
      "name": "Netherlands",
      "region": "EU",
      "pilot": true,
      "lat": 52.2,
      "lon": 5.3,
      "cooling": {
        "gas": { "once_through_sea": 0.5, "once_through": 0.3, "tower": 0.2 },
        "coal": { "once_through_sea": 1.0 },
        "nuclear": { "once_through_sea": 1.0 },
        "biomass": { "once_through_sea": 0.5, "tower": 0.5 }
      }
    },
    {
      "key": "PL",
      "name": "Poland",
      "region": "EU",
      "pilot": true,
      "lat": 52.1,
      "lon": 19.4,
      "cooling": {
        "coal": { "tower": 0.7, "once_through": 0.3 },
        "gas": { "tower": 0.8, "once_through": 0.2 },
        "biomass": { "tower": 0.7, "once_through": 0.3 }
      }
    },
    {
      "key": "SE-SE3",
      "name": "South-Central Sweden",
      "region": "EU",
      "pilot": true,
      "lat": 59.3,
      "lon": 15.0,
      "cooling": {
        "nuclear": { "once_through_sea": 1.0 },
        "biomass": { "once_through_sea": 0.5, "tower": 0.5 },
        "gas": { "once_through_sea": 1.0 }
      }
    },
    {
      "key": "NO-NO1",
      "name": "Eastern Norway",
      "region": "EU",
      "pilot": true,
      "lat": 60.5,
      "lon": 10.8,
      "cooling": {
        "gas": { "once_through_sea": 1.0 },
        "biomass": { "tower": 1.0 }
      }
    },
    {
      "key": "FI",
      "name": "Finland",
      "region": "EU",
      "pilot": true,
      "lat": 62.0,
      "lon": 25.7,
      "cooling": {
        "nuclear": { "once_through_sea": 1.0 },
        "coal": { "once_through_sea": 1.0 },
        "biomass": { "once_through_sea": 0.5, "tower": 0.5 },
        "gas": { "once_through_sea": 1.0 }
      }
    },
    {
      "key": "BE",
      "name": "Belgium",
      "region": "EU",
      "pilot": false,
      "lat": 50.6,
      "lon": 4.6,
      "cooling": {
        "nuclear": { "once_through": 0.5, "tower": 0.5 },
        "gas": { "tower": 0.5, "once_through": 0.5 }
      }
    },
    {
      "key": "GB",
      "name": "Great Britain",
      "region": "EU",
      "pilot": false,
      "lat": 53.5,
      "lon": -1.8,
      "cooling": {
        "nuclear": { "once_through_sea": 1.0 },
        "gas": { "tower": 0.5, "once_through_sea": 0.3, "once_through": 0.2 },
        "biomass": { "tower": 1.0 }
      }
    },
    {
      "key": "CH",
      "name": "Switzerland",
      "region": "EU",
      "pilot": false,
      "lat": 46.8,
      "lon": 8.2,
      "cooling": {
        "nuclear": { "tower": 0.7, "once_through": 0.3 }
      }
    },
    {
      "key": "CZ",
      "name": "Czechia",
      "region": "EU",
      "pilot": false,
      "lat": 49.8,
      "lon": 15.5,
      "cooling": {
        "coal": { "tower": 1.0 },
        "nuclear": { "tower": 1.0 },
        "gas": { "tower": 1.0 }
      }
    },
    {
      "key": "SE-SE4",
      "name": "South Sweden",
      "region": "EU",
      "pilot": false,
      "lat": 56.2,
      "lon": 14.3,
      "cooling": {
        "biomass": { "once_through_sea": 0.5, "tower": 0.5 },
        "gas": { "once_through_sea": 1.0 }
      }
    },
    {
      "key": "NO-NO2",
      "name": "Southern Norway",
      "region": "EU",
      "pilot": false,
      "lat": 59.0,
      "lon": 7.5,
      "cooling": {
        "gas": { "once_through_sea": 1.0 }
      }
    },
    {
      "key": "PT",
      "name": "Portugal",
      "region": "EU",
      "pilot": false,
      "lat": 39.6,
      "lon": -8.0,
      "cooling": {
        "gas": { "once_through_sea": 0.5, "tower": 0.5 }
      }
    },
    {
      "key": "US-TEX-ERCO",
      "name": "ERCOT (Texas)",
      "region": "US",
      "pilot": true,
      "lat": 31.0,
      "lon": -99.0,
      "cooling": {
        "nuclear": { "pond": 1.0 },
        "coal": { "pond": 0.5, "tower": 0.5 },
        "gas": { "tower": 0.6, "pond": 0.2, "dry": 0.2 },
        "biomass": { "tower": 1.0 }
      }
    },
    {
      "key": "US-MIDA-PJM",
      "name": "PJM Interconnection",
      "region": "US",
      "pilot": true,
      "lat": 40.0,
      "lon": -77.5,
      "cooling": {
        "nuclear": { "tower": 0.55, "once_through": 0.25, "once_through_sea": 0.2 },
        "coal": { "tower": 0.6, "once_through": 0.4 },
        "gas": { "tower": 0.7, "once_through": 0.1, "dry": 0.2 },
        "oil": { "once_through": 0.5, "tower": 0.5 },
        "biomass": { "tower": 1.0 }
      }
    },
    {
      "key": "US-CAL-CISO",
      "name": "CAISO (California)",
      "region": "US",
      "pilot": true,
      "lat": 36.8,
      "lon": -119.4,
      "cooling": {
        "nuclear": { "once_through_sea": 1.0 },
        "gas": { "tower": 0.5, "dry": 0.5 },
        "biomass": { "tower": 1.0 }
      }
    },
    {
      "key": "US-MIDW-MISO",
      "name": "MISO (Midcontinent)",
      "region": "US",
      "pilot": true,
      "lat": 42.0,
      "lon": -91.0,
      "cooling": {
        "nuclear": { "tower": 0.6, "once_through": 0.4 },
        "coal": { "once_through": 0.5, "tower": 0.5 },
        "gas": { "tower": 0.7, "once_through": 0.2, "dry": 0.1 }
      }
    },
    {
      "key": "US-SW-AZPS",
      "name": "Arizona Public Service",
      "region": "US",
      "pilot": true,
      "lat": 33.5,
      "lon": -112.1,
      "cooling": {
        "nuclear": { "tower": 1.0 },
        "coal": { "tower": 1.0 },
        "gas": { "tower": 0.5, "dry": 0.5 }
      }
    }
  ]
};
