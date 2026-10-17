# SixthSense v2 - London buses live map (approved 13:38, build now)

Story: every London bus, a second pair of eyes. Admin (TfL bus safety / control room) sees all London buses live,
picks routes, follows a bus, sees which buses need a look, opens the clip + forecast, the post-incident report, and coaching.
Feature reference (features only, never code/branding): Project Orbit live map - route filter, follow bus,
scene 2D/3D/Drone, traffic + CCTV layers, theme light/dark/satellite/night, status tiles (connected, vehicles, latency),
a sorted fleet list panel, clock + weather bar. Our look stays SixthSense (Hark glass, Instrument Serif, minimal).
Stack (user-approved): Mapbox GL JS 3.15.0 (`mapbox-gl` npm), Socket.IO 4.8 (`socket.io-client` 4.8.1 web, `python-socketio` backend).

## Honesty (on screen)
- Bus positions: TfL open data live arrivals, estimated at the bus's next stop. Footer: "Powered by TfL Open Data".
- Camera clips: hackathon footage (SF/NYC) as a labelled stand-in; incident-to-bus pairing is a stand-in, label "Stand-in clip".
- Vision Zero line: "TfL's goal: no one killed on or by a London bus by 2030" linked to
  https://tfl.gov.uk/info-for/media/press-releases/2018/october/london-s-bus-network-to-meet-new-world-leading-bus-safety-standard
- No TfL roundel/logo, no First Bus/Orbit branding, no invented stats.

## Contract (field names exact)
Vehicle {id: str (TfL vehicleId, a registration), route: str, dir: "inbound"|"outbound", towards: str,
  next_stop: str (naptanId), next_stop_name: str, eta_s: int, lon: float, lat: float, bearing: float|null, ts: str ISO}
FleetSnapshot {ts: str, vehicles: Vehicle[], routes: int, latency_ms: int, source: "tfl"}
- Socket.IO (path `/socket.io`, browser connects to `${basePath}/socket.io` i.e. `/app/socket.io` via `path` option):
  server emits `vehicles` (FleetSnapshot) on connect and after every poll.
- GET /api/vehicles -> FleetSnapshot (REST fallback, also used if socket fails).
- GET /api/routes -> [{id, name}]  (all bus routes)
- GET /api/routes/{id} -> {id, directions: [{dir, coords: [[lon,lat],...], stops: [{id,name,lon,lat}]}]} (lazy, cached)
- GET /api/fleet/pairings -> [{incident_id, vehicle_id, route, risk, came_true, mode}] stand-in pairing of real incidents
  (latest run per mode) to live vehicles, stable while the vehicle stays live (cache 30 min).
- GET /api/map-config -> {mapbox_token: str|null}  (from settings MAPBOX_TOKEN via the k8s Secret; never in git)

## Backend notes
- TfL needs a User-Agent header (403 without it from the pod). Optional TFL_APP_KEY setting (app_key param).
- Poll every 30 s in the lifespan task: route ids from /Line/Mode/bus (startup), arrivals via /Line/{comma ids}/Arrivals
  in batches (~20 ids), stay under 45 req/min without a key. Vehicle = earliest prediction per vehicleId.
- Stop coords: /StopPoint/Mode/bus?page=N at startup (cache to settings data dir JSON); position = next stop coords,
  bearing from next to the following stop of the same vehicle when known.
- python-socketio AsyncServer(async_mode="asgi") wrapping the FastAPI app (socketio.ASGIApp), static mount unchanged.
- deploy.sh: put MAPBOX_TOKEN "${MAPBOX_TOKEN:-}" and TFL_APP_KEY in the Secret.

## Web notes
- /dashboard/ = full-screen live map. Left glass panel: route search + selected route chips, Follow bus, status tiles
  (Connected, Vehicles, Routes, Latency). Right glass panel: "Needs a look" (paired buses sorted by risk).
  Top-right: Scene 2D/3D/Drone, layers Traffic/Cameras, theme Light/Dark/Satellite/Night (Mapbox Standard
  lightPreset day/dusk/night; satellite = standard-satellite). Default theme from /api/weather (night after sunset).
  Bottom: clock + weather pill + "Powered by TfL Open Data".
- Buses: one GeoJSON source, circle layer coloured by state (on road blue, needs a look red, watching amber, report filed green).
  Selected route line from /api/routes/{id}. Click bus -> drawer: route, towards, next stop + ETA, and if paired:
  stand-in clip, forecast, agents timeline (spotted -> driver nudged -> pinned -> checked next clip -> report filed),
  buttons Open report (/incident/?id=), Follow, Show route.
- App nav (connects every flow): Live map · Reports · Coaching · How it works. Reports = list of real incidents as
  near-miss reports (filter by camera source road/city/street) with "Show on map" -> /dashboard/?bus=<id>.
  Coaching = per-route weekly card from pairings. Incident detail = report view with "Show on map".
  Deep links: /dashboard/?route=18, /dashboard/?bus=<id>.
- Landing: London buses story (hero "Every London bus, a second pair of eyes."), remove movie lines.
