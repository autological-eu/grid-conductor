# WaterTrace app shell

Build the navigation frame, shared controls and reusable display pieces for WaterTrace, with all eight pages in place holding placeholder content. No backend, no data calls yet.

## What you get

- A left sidebar on desktop and a bottom sheet menu on mobile, listing the eight pages.
- A top bar with the WaterTrace name and a droplet + bolt mark, a zone selector grouped into EU and US, and a light/dark toggle.
- The chosen zone lives in the page address (for example `?zone=DE`), so it stays the same as you move between pages and can be shared as a link. Default: West Denmark (DK-DK1).
- A footer on every page: "Concept MVP · Powered by Electricity Maps data · Water factors: Macknick et al. 2012 (NREL) · Not an official Electricity Maps product".
- Two reusable building blocks: a data label badge (LIVE green / ASSUMPTION amber / CONCEPT · MOCK DATA purple) and a headline-first signal card (big number, one-line meaning, room for a chart).

## Pages and placeholder content

| Page | Address | Placeholder |
| --- | --- | --- |
| Overview | `/` | Hero line, four signal cards (W1–W4) with dashes for values |
| Live Signals | `/live` | W1, W2, W3 cards with LIVE badge and "coming soon" note |
| Forecast & Scheduler | `/forecast` | W4 and W5 sections, empty chart frames |
| Footprint Calculator | `/footprint` | A1 input form skeleton, direct vs indirect result cards |
| Benchmark & Siting | `/benchmark` | A2 ranking table skeleton, map and scatter placeholders |
| Partner Concepts | `/concepts` | X1–X6 cards, all CONCEPT · MOCK DATA |
| Methodology & API | `/methodology` | Glossary, units, scope definitions from the spec |
| Signal Catalogue | `/catalogue` | Table of all signals W1–W5, A1–A2, X1–X6 with status |
