## Technical details

**Routes** (TanStack file routes, one file each): `index.tsx` (rewrites the placeholder), `live.tsx`, `forecast.tsx`, `footprint.tsx`, `benchmark.tsx`, `concepts.tsx`, `methodology.tsx`, `catalogue.tsx`. Each defines its own `head()` with a unique title, description, og:title, og:description.

**Shell**: `__root.tsx` renders `AppShell` around `<Outlet />` — `TopBar`, desktop `Sidebar` (hidden below `md`), `MobileNav` (vaul `Drawer` bottom sheet triggered from the top bar), `SiteFooter`, plus `<Toaster />` from `@/components/ui/sonner`.

**Zone state**: `zone` is a validated root-level search param (`validateSearch` with zod, default `DK-DK1`). A `useZone()` hook reads it via `useSearch({ strict: false })` and sets it with `navigate({ search: prev => ({ ...prev, zone }) })`. Every sidebar/nav `Link` carries `search: prev => prev` so the zone survives navigation. Zones list in `src/lib/zones.ts` as `{ key, label, group: "EU" | "US" }`.

**Theme**: `next-themes`-free — a small `ThemeProvider` writing `.dark` on `<html>` with localStorage persistence, read in a `useEffect` (no SSR mismatch), plus an inline pre-hydration script in the root shell to avoid a flash.

**Design tokens** added to `src/styles.css` in oklch, light and dark: `--navy`, `--water` (primary #1E88E5), `--teal` (low/good), `--amber` (assumption/medium), `--coral` (high), `--concept` (purple), each with a `-foreground` and registered in `@theme inline`. Inter loaded via a `<link>` in the root head. No hardcoded colour utilities in components.

**Components** in `src/components/`:
- `DataBadge.tsx` — `kind: "live" | "assumption" | "mock"`, cva variants → teal/green, amber, purple; labels LIVE / ASSUMPTION / CONCEPT · MOCK DATA. Optional `profiles-illustrative` chip variant.
- `SignalCard.tsx` — props `id`, `title`, `value`, `unit`, `subtitle`, `badge`, optional `children` for a chart slot; headline-first layout (signal id chip, big number + unit, one-line meaning, then children).

**Not in scope here**: any Electricity Maps calls, `waterEngine.ts`, `conceptMocks.ts`, edge function. Pages render static placeholders only.
