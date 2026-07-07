# PHI Guard — Frontend

Enterprise-grade React frontend for the PHI/PII pseudonymization backend. Built
with React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui-style components,
TanStack Query, React Hook Form, Framer Motion, Recharts, and Axios.

This frontend integrates **only** with the existing FastAPI backend endpoints
(`GET /`, `GET /health`, `POST /redact`, `POST /restore`) and does not modify
the backend in any way.

## Getting started

```bash
npm install
cp .env.example .env   # optional — defaults to http://localhost:8000
npm run dev
```

The backend URL can also be changed at runtime from **Settings → Backend
connection**, which is stored in `localStorage` and takes priority over the
`.env` value.

## Scripts

| Command           | Description                              |
| ------------------ | ----------------------------------------- |
| `npm run dev`       | Start the Vite dev server                 |
| `npm run build`     | Type-check (`tsc -b`) and build for prod  |
| `npm run preview`   | Preview the production build locally      |
| `npm run lint`      | Run ESLint                                |

## Pages

- **/** — Landing page with an animated redaction showcase, feature grid, and tech stack
- **/dashboard** — Headline stats, entity distribution pie chart, 7-day activity bar chart, recent activity
- **/redact** — Paste clinical text, redact, view detected entities, copy/download result, session ID
- **/restore** — Restore original text from a session ID + redacted text (also reachable from History)
- **/analytics** — 14-day trend, full entity breakdown, distribution pie chart
- **/history** — Last 20 requests (search, filter by entity type, restore, copy, delete, export JSON)
- **/settings** — Dark mode / theme / animations, backend URL + connection test, export/clear local data
- **404** — Not found page

## Design notes

- All request history is stored **only in the browser** (`localStorage`), capped
  at 20 entries. The original clinical text is **never stored** — only the
  already-redacted output, its entity counts, and the session ID (useful for
  Restore while the backend session is still alive).
- Keyboard shortcuts: `Ctrl/Cmd+Enter` to redact, `Ctrl/Cmd+Shift+R` to reset the redaction form.
- Color mode (light/dark/system), accent theme (cyan/violet/emerald), and animations are all configurable from Settings.
- Routes are code-split with `React.lazy` + `Suspense`; a top-level `ErrorBoundary` guards each layout.

## Production note

This UI helps operate a de-identification workflow. Full HIPAA compliance for
a production deployment also requires access controls, TLS, audit logging
that excludes PHI, encryption at rest, a retention policy, and a signed
business-associate agreement where applicable — see the backend README for
details.
