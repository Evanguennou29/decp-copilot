# Frontend

React + Vite + TypeScript + Tailwind CSS v4. No component library — every
element (table, chips, badges, skeleton) is a bespoke component styled
directly with Tailwind utilities, per `SPEC.md` section 4.

## Development

```bash
cp .env.example .env.local   # set VITE_API_BASE_URL if not localhost:8000
npm ci
npm run dev
```

Requires the API running locally (`make serve` from the repo root) or
`VITE_API_BASE_URL` pointing at a deployed one.

```bash
npm run build     # tsc -b && vite build -> dist/
npm run lint      # eslint .
npm run preview   # serve the production build locally
```

## Design decisions (SPEC.md section 4)

- **Typography**: Space Grotesk only, at both ends of its weight range —
  bold (700) for montants and headings, light (300) for metadata and
  helper text. Montants use `font-variant-numeric: tabular-nums` (the
  `.tabular-figures` class in `src/index.css`) so digits align in a
  column.
- **Palette**: an off-white background (`--color-paper`), dark green ink,
  terracotta for amounts (`--color-money`), and green for interactive
  controls (`--color-accent`).
- **Density**: results render as rows in a real `<table>`, not cards —
  `ResultsTable.tsx` uses `table-fixed` with `line-clamp-2` on the
  description so a long `objet` never blows up a row's height.
- **Five states**, all handled explicitly rather than left to render a
  blank screen: idle (`App.tsx`'s default), loading with a skeleton
  (`SkeletonResults.tsx`, plus a "waking up" hint after 4s in case the
  free-tier API is asleep), error with a retry button (`ErrorState.tsx`),
  no results (`EmptyState.tsx`), and results — themselves split into
  degraded (`ModeBadge` shows "Mode direct — sans clé API", stats and
  table only) and generated (adds `AnswerProse.tsx`'s cited paragraph).
  **Degraded is the default a fresh clone's API serves**, so it was
  designed and tested first, not as an afterthought.
- **Responsive**: `sm:` breakpoints hide the département/date columns
  below 640px, folding that information into a muted second line under
  the objet instead of losing it.
- **Accessibility**: every input has a `<label>`, the table has a
  `sr-only` caption, focus states are a visible 2px outline in the accent
  colour (never removed), and colour is never the only signal (montants
  are also bold and larger).

## Deployment

See the root `README.md`, "Deployment", for the Fly.io + Vercel setup. This
directory deploys to Vercel as a static Vite build (root directory `web/`,
build command `npm run build`, output `dist`), with `VITE_API_BASE_URL` set
to the deployed API URL.
