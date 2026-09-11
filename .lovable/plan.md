# Add a descriptive headline to the map

## What
Add a short, visible headline/label to the main map area so a first-time visitor immediately understands what the visualization represents.

## Where
`src/components/EuropeMap.tsx` — rendered inside the existing map card, above the SVG.

## Proposed headline
"European bidding zones and congested borders — yearly opportunity loss"

## Details
- Place the headline in the top-left corner of the map card, overlaying the SVG on a semi-opaque card background so it remains readable.
- Keep the existing bottom legend that explains the metric toggle and border thickness.
- Use the current `metric` prop to optionally vary wording, e.g. "Market opportunity loss" / "Climate opportunity loss". A single neutral headline is also acceptable.
- Style with the project's semantic tokens (`text-foreground`, `bg-card/90`, `border-border`, `backdrop-blur`) so it stays theme-consistent.
- Keep it concise — one line.

## Acceptance
- The map card shows a readable headline that explains the view.
- No layout breakage on the 1409×960 viewport.
- Build/typecheck passes.
