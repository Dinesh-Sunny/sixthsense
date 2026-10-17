# SixthSense - submission

**Team 43 · VAST Builders Challenge, London, 17 Oct 2026**

**One line:** Every London bus, a second pair of eyes. A video agent that warns before a close call, checks the next clip to see if it really happened, files the near-miss report and turns the pattern into driver coaching, on a live map of every London bus.

- Repo: https://github.com/Dinesh-Sunny/sixthsense
- Live app: https://team-43-app.thecosmoslabs.com/app/ (lab access)
- Weave traces: https://wandb.ai/vastdata/team-43/weave
- Demo video: _link_

## What it does
1. **Live** - all London buses on a Mapbox map from TfL open data, pushed over Socket.IO. Pick a route, follow a bus.
2. **Pre-incident** - VSS search over VastDB finds risky moments; YOLO11 boxes plus a ByteTrack tracker confirm two road users are really closing in; NVIDIA Cosmos3-Reason predicts the next seconds, why, and a fix.
3. **Act** - nudge the driver and pin it on the control room map.
4. **Post-incident** - the agent reads the *next* clip and grades its own forecast with a W&B-hosted judge; a came-true forecast becomes a near-miss report.
5. **Coach** - weekly, per route, from the drivers' own clips.

## Measured today (real run, no hand labels)
- City cameras, 10 clips: 9 warnings, 8 graded, **5 of 8 came true**. An earlier run: 4 of 6. Together **9 of 14**.
- Road and Street: no warnings (no pair closing in fast enough to pass the box check).

## Built on the CAMP stack
VAST VastDB + VSS (search, segments, detections, stream) · NVIDIA Cosmos3-Reason on CoreWeave · YOLO11 · W&B inference + Weave · FastAPI, Next.js 16, Mapbox GL, Socket.IO, deployed on the team's Kubernetes namespace.

## Honest about today
Bus positions are live TfL open data (estimated at each bus's next stop). Camera clips are the hackathon footage (San Francisco and New York) used as a labelled stand-in for bus cameras, and pairing an incident to a live bus is a stand-in too. Every forecast, check and score shown is from our live run.
