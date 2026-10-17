# sixthsense-v1 backend implementation status
- [x] scaffold: backend/ uv package `sixthsense`, deps pinned, opencv-python/matplotlib/av excluded (lock has headless only)
- [x] settings, contracts, clients (http/vss/models), tracing, store (Json+Vast), weather, main, runner
- [x] tracking (HIGH_CONF_DET=0.4 needed: trackers 2.6.1 only births tracks from boxes >= high_conf_det_threshold), pipeline, cli (run/probe)
- [x] tests (69 passing, socket-guarded) + ruff clean
- [ ] deploy/bootstrap.py, deploy.sh (<sha>, sixthsense-v1, /v1, --cutover/--rollback), scripts/release.sh
