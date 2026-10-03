> Historical plan. Preserved for context; completion marks and architecture claims are not current verification. Use [PRODUCT.md](../../PRODUCT.md) and [TASKS.md](../../TASKS.md) for current requirements and priorities.

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
- [x] Move Market/Climate metric toggle from header into the map colour bar
- [x] Header simplified: title + 3-step progress bar + settings menu (Re-import / Recompute targets)
- [x] Daily backend refresh at 05:00 UTC via scheduled job calling /api/public/daily-refresh (updates rolling year + recomputes targets)
- [ ] After publishing: point app_config.daily_refresh_url at the production URL
- [x] Run button spins while a scenario simulates; removed header row-count text; neon green active progress step
- [ ] Overlay official ENTSO-E NTC capacities on inferred capacities in target detection
- [ ] Access control: workbench is currently open to anyone with the link
- [x] Map: larger zone nodes; border lines uniform width colored green→red by opportunity loss; add color bar legend at bottom
- [x] Info hierarchy: numbered start flow in header with primary colour
- [x] Map: connector colour scale grey→red
- [x] Left target sidebar hidden until a target border is clicked; pull-out arrow to reopen
- [x] Right evaluation panel hidden until a scenario is clicked; pull-out arrow to reopen
- [x] Both sidebars resizable via drag handles
- [x] Gamify: drag units from library straight onto the map (drop on country / border)
- [x] Template scenarios: 7 default €1M-normalised scenarios per target, listed at bottom of left sidebar (auto-computed on target open; editable budget; copy to scenarios)
- [x] Show scenario units as emoji/icons pinned on the map (zones and borders)
- [ ] Replace unit emojis with distinct Lucide icons (battery, sun, wind, utility pole, gauge) and simplify library to single-icon cards
- [ ] Restructure scenario unit cards so the icon is primary and editable details sit below it
