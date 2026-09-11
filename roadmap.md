# Roadmap — EU Cross-Border Arbitrage & Investment Simulator

- [x] Enable Cloud, database schema, zone + border seed
- [x] Electricity Maps API key stored
- [x] ENTSO-E API key stored; ENTSO-E used for cross-border flows, demand and capacities
- [x] Chunked historical import (server functions + progress UI)
- [x] Load full year of hourly prices + carbon (41 zones), flows (70 borders), demand (41 zones)
- [x] Map of Europe with zones and yearly metrics
- [x] Target detection + market/climate loss indicators + map target layer (61 targets)
- [x] Network model, base-year replay, validation report (price MAE 7.3 EUR/MWh, direction accuracy 0.98)
- [x] Scenario folders, unit library, drag-and-drop builder, scenario runs
- [x] Evaluation panel with ENTSO-E CBA indicators
- [x] Scenario report view
- [x] Hourly clearing follows ENTSO-E single day-ahead coupling (Euphemia-style ATC welfare maximisation)
- [x] Product pitch/summary for the user

Open / next
- [ ] Overlay official ENTSO-E NTC capacities on inferred capacities in target detection
- [ ] Access control: workbench is currently open to anyone with the link
- [ ] Map: larger zone nodes; border lines uniform width colored green→red by opportunity loss; add color bar legend at bottom
