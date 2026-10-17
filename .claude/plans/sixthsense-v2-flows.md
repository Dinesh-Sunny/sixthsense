# SixthSense v2 - flows audit and plan (14:10)

## Audit of the live app (team-43-app.thecosmoslabs.com/app)
- Dead-click scan (React handlers): no dead buttons; but many things LOOK clickable and are not: card images/play icons,
  whole cards (only "View" works), route chips, the landing hero frame card, map status tiles.
- /reports/ is the old CCTV dashboard (Road/City/Street tabs, "Watch a camera", Ask, Alerts, How it works) - wrong story,
  crowded, no bus or route on any card, no "to review" state.
- /dashboard/ map: three pill groups of controls + two panels + drawer + bottom bar = crowded. Dots too big. Route line missing.
- Missing flows: act on a bus (nudge driver), sign off a report, send it to the garage, go from a report to the map and back,
  coaching -> clips -> report, check new footage (Run) from inside the app, ask the footage from the map.

## Expert hats (decisions)
- Control-room operator (UX): one screen answers "what needs me now"; one list, one drawer; everything else folded away.
- Information architecture: 3 places only - Live, Reports, Coaching. Every object (bus, report, route) links to the other two.
- Interaction design: whole cards/rows are links (one overlay link per card), real buttons only for actions, hover + focus states,
  no element that looks clickable without doing something.
- Visual design (minimal): one glass panel per side, map controls folded into one "Map" popover, faded basemap, small dots.
- Copy (DESIGN.md voice): plain verbs - "Nudge driver", "Sign off", "Send to garage", "Show on map", "Check new footage".
- Honesty: stand-in clip / stand-in pairing labels stay; no fake "sent to driver" - nudge = alert recorded via POST /api/alerts.

## Flows to build
1. Live (owner: map agent)
   - Left panel (collapsible): route search + chips, Follow bus, a single compact status line (Live · 6,328 buses · 537 routes).
   - Right panel: "Needs a look" list (all pairings, sorted by risk, state pill). Selecting a bus swaps the list for the drawer (back arrow).
   - Drawer: clip, forecast, why/fix, timeline, sticky actions: Nudge driver (POST /api/alerts, then timeline ticks "Driver nudged"),
     Open report, Follow. Show route draws the route line.
   - Map controls: ONE "Map" button -> popover with View (2D/3D/Drone), Layers (Traffic, Cameras), Theme (Light/Dark/Satellite/Night).
   - Ask the footage: a small search field in the top bar ("Ask about the footage") opening a results popover (existing /api/ask).
2. Reports (owner: reports agent)
   - Inbox list, one row per real incident: thumbnail, route + bus (from pairings), forecast line, outcome pill, review state
     (To review / Signed off). Filters: All · Came true · Didn't happen · Checking. Camera source filter folded into a select.
   - Header action "Check new footage" -> /run/ (Run page restyled to the same shell, done-state links back to /reports/).
   - Row -> /incident/?id= report: Before / Prediction / What happened / Outcome, evidence (gap chart), agent timeline,
     actions: Sign off (localStorage per viewer, label "Signed off by you"), Send to garage (POST /api/alerts), Show on map
     (/dashboard/?bus=), Coaching for this route (/coaching/?route=). Breadcrumb back to Reports.
3. Coaching (owner: reports agent)
   - Route cards (whole card link) -> /coaching/?route=X detail: the pattern in one line, clips (link to reports),
     one habit to try (from the incidents' fix), Show route on map. Promise line: coaching, not a league table.
4. Shared (owner: reports agent): one AppHeader for every inside page (wordmark -> /, nav Live · Reports · Coaching,
   weather pill), remove leftovers (Watch a camera, Ask panel, Alerts panel, How it works panel, mode tabs from reports).
   Landing CTAs -> /dashboard/. "How it works" lives on the landing only.

## Ownership (avoid conflicts)
- Map agent: components/map/**, views/LiveMapView.tsx, anything only the map uses.
- Reports agent: views/ReportsView, IncidentView/report, CoachingView, Run view, AppHeader/nav, lib/copy.ts.
- lib/api/queries.ts and types.ts: append only, never rewrite others' entries.
