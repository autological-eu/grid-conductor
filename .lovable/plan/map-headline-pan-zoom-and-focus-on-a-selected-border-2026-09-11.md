# Map: headline, pan/zoom, and focus on a selected border

All changes are in `src/components/EuropeMap.tsx` (presentation only). No backend or data changes.

## 1. Headline

Add a one-line headline overlay in the top-left of the map card so a first-time viewer understands the view:

"European bidding zones and congested borders" with a smaller subline that follows the active metric ("Yearly market opportunity loss" / "Yearly climate opportunity loss").

Styled with existing tokens (`bg-card/90`, `border-border`, `text-foreground`, `backdrop-blur`), matching the existing bottom-left legend.

## 2. Pan and zoom

- Wheel/trackpad zoom anchored at the cursor, using exponential scaling from the normalized wheel delta (not a fixed per-event factor), clamped between 1x and 12x.
- Trackpad pinch (wheel with ctrlKey) handled by the same path.
- Drag to pan with pointer events; cursor changes to grabbing while dragging. A drag must not be treated as a click on a border.
- The wheel listener is attached natively with `{ passive: false }` in an effect so the page does not scroll behind the map; handler state read via a ref.
- Transform applied to a single `<g>` wrapping all map content: `translate(x,y) scale(k)`.
- Stroke widths and marker radii divided by the zoom factor so lines and dots stay visually constant while zoomed.
- Small "+ / − / reset" buttons in the top-right corner, zooming about the viewport centre.

## 3. Click a transmission line to focus it

When a border is selected:
- Animate the view to fit the two endpoint zones with padding (compute a target scale/offset from the two projected points, then ease the transform over ~500 ms).
- Highlight the country outlines of the two zones: their country paths get an accent fill and a stronger accent stroke; all other countries stay in the base style.
- All other border lines fade to grey at low opacity; the selected line keeps the accent colour and full opacity.
- Zone markers not belonging to the two focused countries dim.
- Clicking empty map background clears the focus and eases back to the full-Europe view.

Country matching: zone codes carry a country prefix (e.g. `DK-DK1` -> `DK`, `IT-NO` -> `IT`), and the map file has an `iso` property per country. A few features carry `iso: "-99"` (Norway, France, Kosovo), so a small name-to-ISO fallback map is added inside the component.

## Acceptance

- Wheel/pinch zoom keeps the point under the cursor fixed; the page never scrolls behind the map.
- Dragging pans; dragging over a line does not select it.
- Clicking a border zooms to it, outlines both countries, greys the other borders; clicking the background resets.
- Headline is readable at 1409x960 and does not block map interaction other than its own buttons.
- Build and typecheck pass.
