# Roadmap

- [x] WaterTrace app shell: sidebar/mobile nav, top bar with zone selector + theme toggle, footer, DataBadge, SignalCard, 8 placeholder pages
- [x] Backend: secret ELECTRICITYMAPS_API_TOKEN saved
- [x] Backend: em_cache migration staged (applies when the draft is accepted)
- [x] Ported waterEngine.ts, signals.ts, seedData.ts to src/lib (signals imports "./waterEngine"); created src/lib/waterSignals.server.ts (server-only entry, in-memory cache, token from server env)
- [x] Added src/lib/conceptMocks.ts (X1–X6 mock data)
- [ ] Expose water signals to the frontend: TanStack server route or server function calling handleWaterSignals, and wire pages to it
- [ ] Full WaterTrace UI build: data layer, /live, /forecast, /footprint, /benchmark, /concepts, /methodology, /catalogue, overview
- [x] Server token reads ELECTRICITYMAPS_API_TOKEN or ELECTRICITY_MAPS_API_KEY
- [x] All 8 pages built and wired to live data (key working)
