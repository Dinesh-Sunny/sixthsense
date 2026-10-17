# v2 flows - reports agent status (14:40)

Done, `pnpm lint` + `pnpm build` green, checked in headless Chrome at 1280 and 360px against a scratch mock API
(no horizontal overflow; every link/button clicked: nav, filters, source select, row overlay link, Check new footage,
See the reports, Sign off/Undo, Send to garage (idempotent, then "Sent at HH:MM"), See how it decided, Show on map,
Coaching for this route, Show route on map, breadcrumbs, wordmark; no console errors).

## Files
- New: `components/AppHeader.tsx` (wordmark -> /, Live · Reports · Coaching with active state, weather pill),
  `components/ReportRow.tsx` (whole-row overlay link, muted `<video preload="metadata">` thumbnail),
  `lib/signoff.ts` (per-viewer sign-off in localStorage, try/catch + in-memory fallback, useSyncExternalStore).
- Rewritten: `views/ReportsView.tsx` (/reports/ inbox), `views/DetailView.tsx` (/incident/?id= near-miss report),
  `views/CoachingView.tsx` (/coaching/ + ?route=X; page now wraps Suspense).
- Edited: `views/RunView.tsx` (AppHeader shell, title "Check new footage", done -> /reports/), `lib/copy.ts` (appended
  APP_NAV, REPORT_COPY, TIMELINE_STEP, COACHING_COPY, filters, reportId; runSee -> "See the reports"), reports page fallback.
- Not touched: components/map/**, LiveMapView, lib/api/queries.ts + types.ts (no additions needed), backend/.

## Notes for the map agent / lead
- `AppNav` still exists only for LiveMapView and /ask; swap LiveMapView to `<AppHeader />` when convenient, then AppNav,
  ModeTabs, AlertsPanel, IncidentCard and NAV can be deleted.
- Report timeline shows "Driver nudged" whenever an alert exists for the incident; Send to garage and Nudge driver share
  POST /api/alerts, so one alert per incident disables both.
- Review state is per browser (no backend field). "Came true" filter includes Partly; its pill still says Partly.
- Full `pnpm lint` at 14:42 fails only on another agent's new components/landing/** (react-hooks rules); my files lint clean.
