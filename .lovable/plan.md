# Icons, dark mode, neon green & responsive layout

## 1. Better unit icons

Replace the current mappings in `src/lib/unitIcons.tsx` with more literal Lucide icons:

| Unit | Current | New |
|---|---|---|
| Battery (BESS) | `BatteryCharging` | `CarBattery` |
| Solar | `Sun` | `SolarPanel` |
| Wind | `Fan` | `WindTurbine` |
| Transmission line | `Cable` | `UtilityPole` |
| Demand response | `SlidersHorizontal` | `Gauge` |

Any icon not available in the installed lucide-react version falls back to the closest equivalent. The same mapping drives both the sidebar library and the map markers, so both update automatically.

## 2. Larger map icons

- Placed-unit markers on the map currently scale down and stay small. Change them to a constant on-screen size that matches the sidebar library (40 px badge with a 20 px icon, like the sidebar's `size-10` buttons) regardless of zoom level.
- Selected-scenario units stay full colour with a primary ring; other scenarios' units fade back.

## 3. Dark mode

The design tokens in `src/styles.css` already define a `.dark` palette, but nothing toggles it.

- Add a small light/dark toggle (Sun/Moon icon) in the header next to the settings menu.
- Persist the choice in localStorage, defaulting to the user's system preference; apply by toggling the `dark` class on `<html>`.
- Verify map fills, connector colors, and badges read well in both themes (map uses semantic tokens already).

## 4. Neon green primary colour

- Change `--primary` in `src/styles.css` to a neon green (oklch, e.g. `oklch(0.87 0.29 145)` light / slightly brighter in dark) with a dark `--primary-foreground` for contrast.
- This automatically recolours the "start here" button, active progress steps, focused borders, and icon accents.

## 5. Responsive layout

- Below ~1024 px the three-column workbench collapses: map stays full-width; left (targets/scenarios) and right (evaluation) panels become overlay drawers that slide in over the map instead of squeezing it.
- Drag-to-resize handles stay desktop-only; on mobile the drawers use fixed sensible widths (~85vw max).
- Header progress steps shrink to compact numbered dots on small screens.

## Technical notes

- Files touched: `src/lib/unitIcons.tsx`, `src/components/EuropeMap.tsx`, `src/components/DataBar.tsx`, `src/routes/index.tsx`, `src/routes/__root.tsx` (theme init), `src/styles.css`.
- No backend or data changes.
- Verify with typecheck plus a browser pass in both light and dark mode at desktop and mobile widths.
