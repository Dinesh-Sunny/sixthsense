# sixthsense-v1 decisions (R1, final: deadline, no R2)
Inputs: plan, 5 briefs, r1.devil, r1.angel, facts, main-thread facts (a)-(e). Core demo = Main + Detail + Run + self-check score.

### R1.devil.1 Walking skeleton + rollback · adopt · high
Answer: by ~13:30 deploy a skeleton as a SECOND Deployment+Service `sixthsense-v1` (old `sixthsense` at `/app` untouched); check `/healthz`, `/api/incidents`, `/api/clip` 206 through an extra Ingress path `/v1(/|$)(.*)`. Cutover = patch the `/app` Ingress backend to `sixthsense-v1` (basePath stays `/app`); rollback = patch back. Keep `pipeline/` and `app/` until after the demo. No uv cache/PVC: accept cold start (~372 MB after excludes). JSON fallback seeds from a data file inside the release (emptyDir is lost on restart).
Alt: build web with basePath `/v1` (needs rebuild at cutover, rejected); PVC venv cache (time). Evidence: deploy.sh:9-55, plan:50,107,111,145, fact (b).

### R1.devil.2 Scope and one deadline · adopt · high
Answer: freeze 15:30 hard / 15:00 soft (fact c). Re-timebox from 12:45: 12:45-13:30 backend core (settings, contracts, clients+VSSAuth, clip proxy, JsonStore, routes, `sixthsense probe`) + skeleton deploy; 13:30-14:15 tracking + pipeline + road run; web 13:00-14:30 Main/Detail/Run/minimal States; 14:30-15:00 full deploy, cutover, city run; 15:00-15:30 tier 2 in order: EvaluationLogger, Weather, Ask, footer, Mobile polish; cut: Landing, Boxes, Mark-as-handled, Alerts if late. Guards now: TID251 importer bans, secrets-repr test, headless-only lock test, second POST returns active run, clip 206 test, socket guard, ESLint fetch ban; OpenAPI snapshot, hex/href/pipeline-word scans -> `later`. Every brief `[must]` Plan correction overrides plan text.
Evidence: plan:2,107-112,118-129, request.md:46, fact (e).

### R1.devil.3 City pairs + threshold calibration · adopt · high
Answer: track `MODES[mode].classes`; one fresh ByteTrackTracker per class group per clip (vehicles; person+bicycle), key by (group, id); pair filter = at least one vehicle (keeps person-vehicle). Port min 5 shared frames + smoothing; TRACK_ACTIVATION 0.4 and VERIFY_MIN in modes.py. Golden check: old `closing_gap` vs new on the 3 road clips' saved detections (gitignored) before wiring; test "person+car pair verifies in city".
Evidence: pipeline/run.py:64-66 (per-label linking), :101-102 (one vehicle), modes.py:33-43, brief-cv:10-11, fact (d).

### R1.devil.4 Publish path · assumption · medium
Answer: drop `gh release`. `scripts/release.sh` builds in the workspace and pushes an orphan `dist` branch (web/out + backend src + uv.lock) via the git proxy; pod initContainer fetches `codeload.github.com/.../tar.gz/<commit-sha>` (SHA pin = integrity; skip sha256 of codeload archives, not byte-stable). `deploy.sh <sha>` arg; VM does `git pull && bash deploy.sh <sha>`. Record the build-output exception (dist branch only) in AGENTS.md Workflow.
Alt: node initContainer build in pod (npm egress unverified). Evidence: fact (a), devil:4, .claude/rules/git.md.

### R1.devil.5 Pod egress + secrets + lab TLS · adopt · high
Answer: Secret gains COSMOS3_REASON_URL, YOLO_URL/GPU_HOST, WANDB_TEAM/PROJECT, S3_ENDPOINT, ACCESS_KEY, SECRET_KEY, VASTDB_BUCKET. `sixthsense probe` runs inside the skeleton pod: VSS login, Cosmos/YOLO `/v1/models`, W&B inference, weave.init, VastDB type probe (shapes and ok/fail only). `vss_verify_tls` and `vast_ssl_verify` default False (lab-only, commented); public clients keep verify on.
Evidence: pipeline/models.py:11-14, pipeline/vss.py:9, deploy.sh:14-17, brief-data:23, facts:12.

### R1.devil.6 Public run/ask/alert abuse · adopt · medium
Answer: `RUNS_ENABLED` setting + 60 s cooldown after a run finishes (in RunStatus); `/api/ask` behind `Semaphore(2)`; Discord payload `allowed_mentions: {"parse": []}`, text capped (~1,500 chars). No auth today.
Evidence: plan:8,58-60, brief-backend:10, brief-llm:13, deploy.sh:44-53.

### R1.devil.7 Metrics population + accuracy definition · adopt · high
Answer: incidents carry `run_id`; list + metrics show only the latest finished run per mode (old replace-by-mode semantics). Metrics computed once at run end into an insert-only `runs` row (see angel.4). Screen copy "N of M came true" (yes/checked); Partly shown as its own count; drop the 0.5 partial-credit figure. Sample label per incident; fixtures never feed metrics (test).
Evidence: pipeline/run.py:268-282, DESIGN.md:13, brief-data:12-13.

### R1.angel.1 Weave EvaluationLogger per run · assumption · medium
Answer: tier 2 (first after core): `tracing.log_evaluation(mode, run_id, incidents)` via `to_thread`, skip `unknown`, no-op untraced; `eval_url` optional on the runs row/ModeMetrics. Check Evals-tab render once live.
Evidence: weave wheel eval_imperative.py:694,902,1074,1113 (confirmed in scratchpad extract).

### R1.angel.2 Dual graders + gap trend · reject · high
Answer: later. Doubles judge calls under the W&B concurrency cap, needs new contract fields; no time. Evidence: brief-llm:13, fact (c).

### R1.angel.3 Video vs text forecast comparison CLI · reject · high
Answer: later (README "next steps"). Extra GPU runs in the freeze window. Evidence: fact (c), devil.2.

### R1.angel.4 VastDB as system of record · assumption · medium
Answer: add scalar `run_id`, `came_true` (utf8) to `incidents` and an insert-only `runs` table (`run_id, mode, finished_ms, candidates, verified, checked, yes, partly, eval_url`); include in the step-1 type probe. `camera_id`/`source` columns and column-only metric pushdown -> later.
Evidence: brief-data:11-14,17-19, vastdb.yaml vdb-select/vdb-predicate.

### R1.angel.5 Proof in the UI · assumption · medium
Answer: tier 2: footer "Saved in VastDB" only when `store_backend=="vast"`, else "Saved locally"; eval link inside "See how it decided" only if angel.1 ships. Copy via lib/copy.ts per VOICE.md.
Evidence: brief-data:22, brief-web:10.

### R1.angel.6 weave.thread + published prompts · assumption · medium
Answer: `with weave.thread(run_id)` around run_mode in tracing.py (tier 2, 2 lines); StringPrompt publishing rejected (startup network write, no time).
Evidence: weave/trace/api.py:566 (angel), brief-llm:28.

### R1.angel.7 GitHub Actions CI · reject · medium
Answer: later. Workflow-file pushes may need a `workflow`-scoped token through the proxy (unverified) and a red public badge is a demo risk; guards run in release.sh.
Evidence: fact (a), devil.2.

### R1.judge.1 Font deps with lib_check REVIEW · escalate · medium
Answer: default adopt `geist` 1.8.1 + local Instrument Serif woff2 from `@fontsource/instrument-serif` (one importer `web/src/app/fonts.ts`); if declined, system-ui stack, no deps. Standards: REVIEW -> human decides.
Evidence: plan Stack suggestions row, facts:7-8, standards.md gate 3.

## Plan changes
- Request analysis/Acceptance: one deadline (15:00 soft, 15:30 freeze); acceptance 4 (weather) and 5 (guards) reduced to tier 2 / demo guards (d2); acceptance 3 needs RUNS_ENABLED + cooldown (d6).
- Open questions: Q1 closed (codeload by SHA, fact a); probe moves into the skeleton pod and adds GPU/W&B/weave/VastDB (d5).
- Architecture fit: keep `pipeline/`, `app/` until after the demo (d1).
- Endpoints: metrics from latest `runs` row, "N of M came true", `eval_url` optional (d7, a1, a4); Discord allowed_mentions + cap; ask semaphore (d6).
- Library decisions: verify = per-class-group trackers, at-least-one-vehicle pair filter, activation 0.4 (d3); store adds `run_id`, `came_true`, `runs` table (a4); Settings lab-TLS defaults False, new Secret keys (d5); brief [must] corrections override (d2).
- File placement: `scripts/release.sh` pushes `dist` branch; `deploy.sh <sha>` creates `sixthsense-v1` + `/v1` path, cutover patch (d1, d4).
- Implementation plan: re-timeboxed tiers per d2; golden check before pipeline wiring (d3); tier 2 adds EvaluationLogger, weave.thread, storage footer (a1, a5, a6).
- Best practices: defer OpenAPI snapshot, hex/href/pipeline-word scans to later (d2).
- Docs plan: README "later" adds dual graders, video-vs-text compare, CI (a2, a3, a7); AGENTS.md records dist-branch exception (d4).
