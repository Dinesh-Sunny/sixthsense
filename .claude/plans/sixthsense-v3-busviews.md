# SixthSense v3 - bus camera views only (personal polish, after submission)

## Finding (17 Oct, 17:00): the archive's vehicle-mounted cameras
- `pie_cam-3` - 180 videos, windscreen dashcam with the bonnet in frame (PIE pedestrian-intention dataset, Toronto). Use as the **bus front camera** stand-in.
- `nyc_bike_gopro-1` - 78 videos, low GoPro on New York bike lanes, close to the kerb. Use as the **nearside camera** stand-in.
- All other 11 cameras are fixed (street, highway, warehouse, indoor). They leave every screen.
- Honest label everywhere: "Stand-in footage: a car dashcam (front) and a bike camera (nearside), not a London bus".

## Backend
1. Modes `bus_front` (pie_cam-3) and `bus_nearside` (nyc_bike_gopro-1), each with its own hazard searches:
   - front: pedestrian about to step out in front, pedestrian crossing ahead, cyclist ahead in lane, vehicle cutting in ahead, car pulling out from the side, vehicle braking ahead, blocked lane ahead, turning across a crossing.
   - nearside: cyclist alongside on the nearside, pedestrian close to the kerb, car door or parked car near the lane, scooter weaving, vehicle overtaking close, bus stop crowd at the kerb.
2. Ego check (new, both modes): the camera vehicle itself has no box, so pair gaps don't apply. Track road users with ByteTrack and score
   "closing on us": box height growth (scale expansion -> time-to-contact proxy, TTC ~= dt / (s - 1)) plus how close the box is to the
   bottom-centre lane zone. Keep the clip when a tracked person/bike/vehicle in the lane zone grows by >= 35% within <= 2 s, or TTC proxy <= 3 s.
   verify_note in plain words: "a pedestrian ahead grew 1.8x in 1.2 s, about 2 s from the front of the bus". Keep the pair check for fixed cameras.
3. Prompt: "You are a London bus safety analyst. This is the bus's front (or nearside) camera..." with the fixed hazard set per mode; fix = advice to the driver.
4. CLI: allow `--limit` up to 60 for runs (API run cap stays 10). Round-robin over hazard queries, skip near-duplicates.
5. Pairings and metrics prefer the latest `bus_front` + `bus_nearside` runs; fall back to `bus`, then `city`.
6. Expose `camera_view: "front" | "nearside"` on incidents (from mode) - append to contracts.

## Web
1. Default data = bus_front + bus_nearside everywhere (map, reports, report, coaching, landing). Fixed-camera incidents never show.
2. Landing: replace the SF/NYC static frames with frames from these two cameras (front for the hero/forecast, nearside for coaching/false-alarms),
   pulled from real incidents' clips; the step-2 creative shows the ego "closing on us" box growing instead of two boxes meeting.
3. Show the view as a small label on clips: "Front camera" / "Nearside camera" + the honest stand-in note.
4. Reports filter: All views / Front / Nearside.
