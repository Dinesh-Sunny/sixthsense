# SixthSense v1 - library-first rebuild (tier L, R1) - plan
Brief: `sixthsense-v1.request.md` (user decisions, not re-asked) · facts: `sixthsense-v1.facts.md` · deadline 15:30 slice / 16:30 demo.
**Summary.** `backend/` uv package `sixthsense` (FastAPI + async pipeline: httpx/tenacity VSS client, openai SDK for Cosmos + W&B, supervision+trackers verify, Weave ops, VastDB store) serves `web/out` (Next 16 static export, shadcn, TanStack Query) under Ingress `/app`. Pod = python:3.12-slim; initContainer pulls a GitHub release tarball, checks sha256, `uv sync --locked`. Sky atmosphere = Open-Meteo weather fetched and cached by the pod. 100k-DAU pieces documented, marked `later`.

## Request analysis
- Goal: replace hand-rolled HTTP/tracking/JSON code with library APIs; implement approved wireframes (Main, Detail, Ask, States, Run, Mobile, Weather; Landing last) with real data only.
- Acceptance: (1) `uv run sixthsense run --mode road --limit 3` on the VM writes verified incidents to VastDB (JSON fallback flag); (2) cluster `/app/` serves Main/Detail/Run/Ask from the static export with clips seekable (206); (3) "Watch a camera" starts an in-pod run with live step progress; (4) header pill shows live London weather and the matching `wx-*` sky; (5) ruff + pytest green, every guard below proven to bite; (6) README + `docs/architecture.md` describe slice vs 100k-DAU target.
- Assumptions: weather city = London (wireframes; footage is archive, so camera-city weather "now" would mislead); GitHub repo public (else add read-only `GITHUB_TOKEN` to the Secret); one replica today; no end-user auth (hackathon) - GPU runs guarded by a single-flight lock.
- Open questions (none BLOCKING): Q1 release-asset host `release-assets.githubusercontent.com` reachable from pod? (step 0 probe; fallback = codeload tarball of a `dist` tag); Q2 pod egress to `api.open-meteo.com`? (fallback = clock-based day/night sky, no label); Q3 VastDB data VIP reachable from pod? (fallback `STORE_BACKEND=json`).

## Stacks involved
| stack | installed version | role | needs stack-expert? |
|---|---|---|---|
| fastapi (+pydantic 2.14.1, pydantic-settings 2.16.0, starlette 1.8.0) | 0.143.3 | API, settings, static serving, Range proxy | yes |
| arq-httpx (httpx 0.28.1, tenacity 9.2.1; arq later) | - | VSS/YOLO/Open-Meteo/Discord client, retries | yes |
| weave (+openai 3.33.0 / httpx2) | 0.53.12 | Cosmos + W&B calls, structured output, tracing | yes |
| supervision (+trackers 2.6.1) | 0.31.0 | Detections, ByteTrackTracker, anchors | yes |
| vastdb (+pyarrow 23, ibis 10.8) | 2.1.0 | incidents/alerts tables | yes |
| next / react | 16.3.8 / 19.2.8 | static export UI | yes (one expert for both) |
| shadcn-ui (Tailwind v4, radix base) | 4.21.1 | components + tokens | yes |
| tanstack-query | 5.104.3 | client data, polling | yes |
| uv / ruff / pytest | 0.12.15 / 0.16.10 / 9.1.1 | packaging, lint bans, tests | no (covered in enforcement) |

## Stack leverage
| stack | status | lens grid (adopt now) | later |
|---|---|---|---|
| fastapi | touched | best-practice: fa-lifespan, fa-depends, fa-settings, fa-response-model, fa-model-config · perf: fa-httpx-client, fa-gzip (JSON only) · reliability: fa-staticfiles, fa-streaming, fa-health · testing: TestClient-in-`with` (lifespan) | fa-frontend (untested with Next export), fa-background-tasks->queue, fa-workers (HPA) |
| arq-httpx | touched | hx-asyncclient, hx-limits, hx-timeout, hx-stream, hx-range, hx-event-hooks (timing log, no headers) · tn-async-retrying, tn-wait-jitter, tn-stop, tn-retry-if · aq-simple-or-arq (TaskGroup+Semaphore) | aq-worker-settings, aq-create-pool, aq-enqueue-job (_job_id=source), aq-retry, aq-cron-fn, aq-health, hx-http2 |
| weave | touched | wv-init, wv-op (kind=llm/tool, postprocess_inputs), wv-openai-autopatch, wv-inference-trace, wv-attributes (mode, run_id), oa-asyncclient, oa-retries, oa-parse (probe-gated), wv-gotcha-video | wv-eval + wv-scorer-class (self-check as Scorer), wv-thread, wv-semaphore, oa-raw |
| supervision | touched | sv-detections-ctor, sv-detections-empty, sv-filter-mask, sv-anchors (CENTER), sv-pair-distance, sv-trackers-install, sv-bytetrack-params, sv-bytetrack-update, sv-tracker-reset (fresh per clip); avoid sv-bytetrack-removed | sv-box/label/trace-annotator thumbnails, sv-polygonzone lanes |
| vastdb | touched | vdb-connect-fn, vdb-transaction, vdb-endpoints, vdb-create-schema/table (fail_if_exists=False), vdb-insert, vdb-upsert-pattern, vdb-row-id, vdb-update, vdb-select (columns), vdb-predicate, vdb-limit, vdb-sort-client, vdb-many-reads (5 s cache) | vdb-backoff tuning, vdb-query-config |
| tanstack-query | touched | tsq-provider, tsq-stale-gc-tuning, tsq-query-keys, tsq-query-options, tsq-use-suspense-query, tsq-refetch-interval, tsq-optimistic-ui (Send alert), tsq-prefetch-hover (`queryClient.query`), tsq-no-server-hydration | tsq-devtools, tsq-optimistic-cache |
| next | touched | guide-static-exports, cfg-base-path, cfg-trailing-slash, images-config (unoptimized), use-search-params-hook (+Suspense), fonts (next/font/local), next-config (poweredByHeader false), eslint-config, guide-videos, typed-routes | react-compiler, guide-cdn-caching, cfg-asset-prefix (CDN) |
| react | touched | suspense, use-transition (mode tabs), use-optimistic | compiler-install |
| shadcn-ui | touched | sh-init (-b radix), sh-components-json, sh-css-variables, sh-theme-inline, sh-add-token, sh-tailwind-v4, sh-button, sh-tabs, sh-badge, sh-card, sh-skeleton, sh-empty, sh-sonner, sh-input-group, sh-shimmer ("Asking…"), sh-cva | sh-mcp, sh-dark-mode |
| uv / ruff / pytest | touched | uv-init(--package), uv-build-backend, uv-dependency-groups, uv-resolution-controls (exclude-dependencies), uv-lock-check, uv-project-env · tid251-banned-api, tid251-sanctioned-home, rules-async, rules-pytest · an-mode, iso-network-block, iso-monkeypatch, cfg-strict | uv-audit, mypy outline (typing gate) |
| web-tooling | enhances | es-no-restricted-imports / no-restricted-globals as web choke-point guards | prettier |
| web-testing | later | vt-msw + rtl-render for Ask/Run states | - |
| mypy, zustand, langchain*, langgraph, langsmith, langfuse, assistant-ui, react-bits, freellmapi, omniroute | n/a | no type gate today / no client state beyond Query / no agent framework, chat UI, motion or LLM router needed | - |
Next-step-up (advanced, requires used): vdb-many-reads (adopt), wv-semaphore (later: needs wv-eval).

## Stack suggestions
| candidate | supports | hidden opportunity | gate results | cost | adopt-now/later |
|---|---|---|---|---|---|
| geist + @fontsource/instrument-serif | next fonts | Google Fonts blocked from workspace (facts) so next/font/google breaks the build | 1 real need, 2 ok, 3 REVIEW (unknown facts; geist 1.8.1 Vercel, OFL), 4 ~0.2 MB, 5 one importer `web/src/app/fonts.ts` | 2 npm deps | adopt-now (human confirms REVIEW) |
Rejected: openapi-typescript (gate 3 FAIL idle) -> hand-written TS mirror + OpenAPI snapshot test. Removal: `opencv-python` (via trackers) excluded for `opencv-python-headless` (slim has no libGL).

## Architecture fit
- Port, don't redesign: watch/verify/foresee/selfcheck/run (`pipeline/run.py:35-273`), prompts FORESEE/JUDGE (`run.py:156-237`), MODES (`pipeline/modes.py:2`), closing-gap rule 1.5 cl + 5 shared frames + smoothing (`run.py:89-123`), VSS endpoints (`pipeline/vss.py:101-139`), Range proxy (`app/main.py:105-121`), parse_json think-strip (`pipeline/models.py:87`).
- Delete after port: `pipeline/`, `app/` (stdlib-only rule retires), `first()` lookups (Pydantic models with `extra="ignore"` replace them).

### Endpoints and data contract (`contracts.py`, mirrored in `web/src/lib/api/types.ts`)
| route | returns | notes |
|---|---|---|
| `GET /healthz` · `GET /readyz` | `{ok}` | liveness no I/O; readiness = VSS token + store ping |
| `GET /api/incidents?mode=` · `GET /api/incidents/{id}` | `list[Incident]` · `Incident` | risk desc; Incident = old row keys + `gap_series: list[GapPoint(t,cl)]`, `fixture` -> "Sample" |
| `GET /api/metrics` | `list[ModeMetrics]` | candidates, ruled_out, verified, checked, came_true_yes/partly, accuracy, generated_at |
| `POST /api/runs {mode,limit}` · `GET /api/runs/current` | `RunStatus` (202) | steps find/rule_out/predict/check `{done,total,state}`; second POST returns the active run |
| `POST /api/ask {question, original_video?}` | `AskOut{answer, evidence[]}` | proxies VSS `/agent/ask`; shape recorded by probe |
| `POST /api/alerts {incident_id}` · `GET /api/alerts` | `Alert` · `list[Alert]` | server builds alert from stored incident (client fields untrusted), Discord webhook via shared client |
| `GET /api/clip?source=s3://…` | 200/206 stream | source must match `settings.clip_bucket` prefix |
| `GET /api/weather` | `Weather{city,temp_c,label,wx: clear|cloudy|rain|night,source: open-meteo|clock}` | WMO 0-1 clear, 2-3/45/48/71-77/85-86 cloudy, 51-67/80-82/95-99 rain, `is_day=0` night; UI sets `wx-*` on the Atmosphere wrapper |
Flow: `run_mode` -> watch (search per query x camera, `gather` under semaphore, dedupe by source) -> verify (VSS detections, else YOLO, -> tracking; street = Cosmos yes/no) -> foresee (Cosmos on clip -> `Forecast`) -> selfcheck (next segment; `SELFCHECK_VIA=video` Cosmos watches it, else Llama-3.3-70B judges text) -> `store.upsert` -> metrics; each step a Weave op with `weave.attributes({mode, run_id})`.

## Library & API decisions
| need | choice | why vs alternatives | version | doc ref |
|---|---|---|---|---|
| config | `Settings(BaseSettings)` + `@lru_cache get_settings`, `SecretStr` for secrets, `validation_alias=AliasChoices("VSS_URL","INGRESS_URL")` | replaces team_config()/os.environ | 2.16.0 | fa-settings |
| HTTP | one `httpx.AsyncClient` per upstream (VSS, GPU, public) built in lifespan; `httpx.Timeout(10, read=120)`; `verify=settings.vss_verify_tls` | pooling; urllib per call today | 0.28.1 | fa-lifespan, hx-asyncclient, hx-timeout |
| VSS auth | `VSSAuth(httpx.Auth)`, `requires_response_body=True`, `auth_flow`: login if no token, Bearer, on 401 re-login + retry once | library-native token refresh | 0.28.1 | python-httpx.org/advanced/authentication |
| retries | `AsyncRetrying(stop=stop_after_attempt(4), wait=wait_exponential_jitter(initial=0.5,max=8), retry=retry_if_exception(is_transient), reraise=True)` | 429/5xx/transport only | 9.2.1 | tn-* |
| clip proxy | `client.send(req, stream=True)` -> `StreamingResponse(r.aiter_bytes(), status_code=r.status_code, headers={Content-Type,Length,Range,Accept-Ranges})`, `background=BackgroundTask(r.aclose)` | forwards Range, 206 | 0.143.3 | fa-streaming, hx-stream |
| LLM/VLM | `AsyncOpenAI(base_url=cosmos_url, api_key=gpu_token, max_retries=2, timeout=httpx2.Timeout(120))`; W&B: `AsyncOpenAI(base_url=…/v1, api_key=wandb, project=f"{team}/{project}")`; content part `{"type":"video_url",…}` | replaces raw POST | openai 3.33.0 | oa-asyncclient, wv-inference-trace |
| JSON output | `chat.completions.parse(response_format=Forecast)`; if probe shows unsupported: `create` + `Forecast.model_validate_json(extract_json(text))` | typed, validated | 3.33.0 | oa-parse |
| tracing | `weave.init(f"{team}/{project}")` only if key set; `@weave.op(kind=…, postprocess_inputs=drop_bytes)` | autopatch nests openai spans | 0.53.12 | wv-init, wv-op, wv-gotcha-video |
| verify | `sv.Detections(xyxy, confidence, class_id, data={"class_name"})` per frame -> fresh `ByteTrackTracker(frame_rate=fps, …)` per clip -> `tracker.update(d)` -> `[tracker_id>=0]` -> `get_anchors_coordinates(sv.Position.CENTER)`; pair gap / mean box diagonal (hand-written: no built-in, sv-pair-distance) | replaces _iou/_tracks | sv 0.31.0, trackers 2.6.1 | sv-* (confirm activation/IoU kwarg names via `help()`) |
| store | `vastdb.connect(endpoint=S3_ENDPOINT, access, secret, ssl_verify=False)`; schema `sixthsense`, tables `incidents`, `alerts`; upsert = select `$row_id` by id then update/insert in one tx; sync SDK via `anyio.to_thread.run_sync` | no upsert/order_by in 2.1 | 2.1.0 | vdb-* |
| run jobs | `asyncio.TaskGroup` + `Semaphore(settings.gpu_concurrency=3)`; single-flight `asyncio.Lock`; status in `app.state` | arq needs Redis (later) | stdlib | aq-simple-or-arq |
| weather | `GET https://api.open-meteo.com/v1/forecast?latitude&longitude&current=temperature_2m,weather_code,is_day&timezone=auto`; 10-min server cache + `Cache-Control: public, max-age=600` | keyless; free tier 10k calls/day so never browser-direct at scale; CC BY 4.0 credit | v1 | open-meteo.com/en/docs, /en/terms |
| web data | `queryOptions` factories; `useSuspenseQuery`; runs `refetchInterval: q => q.state.data?.state==="running" ? 2000 : false` | static export: client fetch only | 5.104.3 | tsq-* |
| TS types | hand-written `web/src/lib/api/types.ts` mirroring `contracts.py`; pytest snapshot of `app.openapi()` -> `backend/tests/openapi.snapshot.json` flags drift | generator failed gate 3 | - | decisions |
Deprecated avoided: `sv.ByteTrack`, `update_with_detections`, `on_event`, `prefetchQuery`, `next lint`, `httpx.Timeout` in openai 3.

## File placement
| path | new/modify | owns | why here |
|---|---|---|---|
| `backend/pyproject.toml`, `uv.lock`, `.python-version` | new | deps (`[dependency-groups] dev`: ruff, pytest), `[tool.uv] exclude-dependencies=["opencv-python"]` + `opencv-python-headless`, ruff bans, pytest cfg | uv-init --package, uv-build-backend |
| `backend/src/sixthsense/settings.py` | new | Settings, get_settings, SettingsDep | fa-settings |
| `…/contracts.py` | new | API models: Incident, GapPoint, ModeMetrics, RunStatus/StepProgress, AskIn/AskOut, Alert, Weather | one home for the contract |
| `…/modes.py` | move | MODES, COCO label->id, CLOSE_CL=1.5, thresholds | code-style.md constants home |
| `…/clients/http.py` | new | AsyncClient factories, VSSAuth, retry policy | sanctioned httpx importer |
| `…/clients/vss.py` | new | VSS calls + response models (SearchHit, Segment, DetectionsResp) | upstream boundary |
| `…/clients/models.py` | new | cosmos(), llm(), yolo(), extract_json | sanctioned openai importer |
| `…/tracing.py` | new | init_tracing, `op` re-export, drop_bytes | sanctioned weave importer |
| `…/tracking.py` | new | to_detections, closing_gap -> (score, note, gap_series) | sanctioned supervision/trackers importer |
| `…/pipeline.py` | new | watch/verify/foresee/selfcheck/run_mode(progress cb) | domain logic |
| `…/store.py` | new | IncidentStore protocol; VastStore, JsonStore; Sample fixtures only when empty | sanctioned vastdb importer |
| `…/weather.py` | new | Open-Meteo fetch, WMO->wx map, TTL cache | one concern |
| `…/main.py` | new | app factory, lifespan, `/api` APIRouter, health, static mount last | fa-lifespan |
| `…/cli.py` | new | `sixthsense run|probe` (`[project.scripts]`) | uv-entry-points |
| `backend/tests/*` | new | see Test plan | pytest |
| `web/` (create-next-app --no-agents-md, src/) | new | `app/{layout,page,incident/page,run/page,ask?}.tsx`, `components/{IncidentCard,StatusPill,AskBox,AlertRow,AccuracyMeter,WeatherPill,Atmosphere}.tsx`, `lib/api/{client,queries,types}.ts`, `lib/copy.ts`, `app/globals.css` (tokens.json -> CSS vars + wx-*), `app/fonts.ts` | next project-structure, sh-components-json |
| `deploy/bootstrap.py`, `deploy.sh`, `scripts/release.sh` | new/modify | pod init, k8s apply, build+release | repo convention |
| `docs/architecture.md`, README, AGENTS.md (commands/stack), `.claude/rules/{backend,web}.md` | new/modify | slice vs 100k target, guards | standards › Docs |

## Implementation plan (time boxes; Landing is the first cut)
0. 12:15-12:30 Scaffold `uv init --package backend`, `uv add …` pinned; `pnpm create next-app web --ts --tailwind --eslint --app --src-dir --no-agents-md`; `pnpm dlx shadcn@4.21.1 init -b radix`. On VM: run a throwaway python:3.12-slim pod that answers Q1-Q3 and `import cv2, supervision, trackers` after `uv sync`.
1. 12:30-13:15 settings, contracts, clients/http+vss (probe shapes -> models), clients/models, tracing, store (Json first, Vast second), weather, main routes; tests for each. Port `probe.py` as `sixthsense probe` (prints shapes, never values).
2. 13:15-13:50 tracking.py (+synthetic tests), pipeline.py async port with progress callback, CLI; run `--mode road --limit 3` on VM -> VastDB.
3. 12:45-14:30 (parallel) web: tokens -> globals.css, fonts, providers, api client/queries, Atmosphere+WeatherPill, Main, Detail (`/incident/?id=`; video + gap chart from gap_series; "Boxes on" later), Run (POST + poll), Ask (5 states), States (loading/sample/empty/error), Mobile layout (responsive Detail + Discord text). Copy verbatim from wireframes per DESIGN.md.
4. 14:30-15:00 `scripts/release.sh`: `uv lock --check`, `pnpm install --frozen-lockfile && pnpm build`, tar `backend/{pyproject.toml,uv.lock,src}` + `web/out`, sha256, `gh release create`. `deploy.sh`: Secret (+ACCESS_KEY, SECRET_KEY, S3_ENDPOINT, VASTDB_BUCKET, WANDB_TEAM/PROJECT), ConfigMap `sixthsense-boot` (bootstrap.py, RELEASE_URL, RELEASE_SHA256), Deployment initContainer -> emptyDir `/srv` (`UV_PYTHON_DOWNLOADS=never`, `UV_PROJECT_ENVIRONMENT=/srv/venv`, `uv sync --locked --no-dev --no-editable`), app container `/srv/venv/bin/uvicorn sixthsense.main:app --host 0.0.0.0 --port 8080`, probes /healthz + /readyz, rollout timeout 600 s; keep existing Service/Ingress.
5. 15:00-15:30 Real runs road/city/street from the app, README + docs/architecture.md, registry rows (`stacks.sh bootstrap --write`), Landing at `/about/` if time.
Hand-written (justified): pair-gap metric, WMO->wx table, extract_json, VSSAuth flow body, 10-min weather cache (one timestamp check), bootstrap.py (stdlib: pod has no curl).

## Best practices & enforcement
| practice | doc ref | guard |
|---|---|---|
| one sanctioned importer each: httpx.AsyncClient (clients/http.py), openai (clients/models.py), weave (tracing.py), vastdb (store.py), supervision/trackers (tracking.py) | standards N7, tid251-* | ruff TID251 bans + per-file-ignores; `test_conventions.py` asserts config + a bite fixture |
| no hand-rolled HTTP / server | brief | TID251 bans `urllib.request`, `http.server`, `requests` repo-wide |
| config only via Settings; secrets SecretStr | fa-settings | TID251 bans `os.environ`, `os.getenv` outside settings.py; test repr(Settings) hides secrets |
| removed APIs | sv-bytetrack-removed | TID251 bans `supervision.ByteTrack` |
| every `/api` route has response_model; static mount last; health before mount | fa-response-model, fa-staticfiles | `test_conventions.py` walks `app.routes` |
| contract drift | decisions | OpenAPI snapshot test |
| no blocking calls in async code | rules-async | ruff ASYNC rules |
| tests never hit network | iso-network-block | autouse socket guard in conftest |
| bounded GPU concurrency + single run | aq-simple-or-arq | test: second POST /api/runs returns current run |
| web fetch only via `lib/api/client.ts` (basePath, throws on non-2xx) | tsq-no-server-hydration | ESLint `no-restricted-globals: fetch` except `src/lib/api/**` |
| colours only from tokens; no pipeline words on screen; Sample label on fixtures | DESIGN.md | convention test scans `web/src/**/*.tsx` for raw hex and YOLO/Cosmos/segment/inference outside "See how it decided" |
| locked installs | uv-lock-check | release.sh fails on `uv lock --check` / `--frozen-lockfile` |

## Docs plan
README: run/build/deploy commands, live-vs-Sample, Open-Meteo credit. `docs/architecture.md`: slice diagram + 100k-DAU target (`later`: arq workers on Redis with `_job_id=source`, DataEngine event triggers replace polling search, Redis cache for incidents/weather, CDN for `web/out` via assetPrefix, HPA with ≥2 replicas once run state leaves memory, prebuilt image or PVC uv cache, Weave Evaluation scorer, auth). AGENTS.md: Stack/Commands/Conventions (stdlib-only rule and `first()` rule retire); code-style.md constants path.

## Test plan
pytest (anyio auto mode, no network): tracking (converging pair -> verified + gap_series; empty frames; `-1` ids dropped; non-vehicle pairs ignored), VSS models parse probe-shaped fixtures, VSSAuth re-login on 401 (`httpx.MockTransport`), retry only 429/5xx, clip proxy forwards Range and returns 206 + Content-Range, weather WMO table (parametrized) + is_day=0 -> night, store JsonStore upsert idempotent, API via `with TestClient(app)` + `dependency_overrides`, conventions + OpenAPI snapshot. Web: `pnpm lint && pnpm build` (tsc). Live: `sixthsense probe`, road run limit 3, browser check of seek/weather on cluster.

## Risks
| risk | mitigation |
|---|---|
| opencv-python needs libGL on slim | uv exclude-dependencies + headless; step-0 import smoke |
| release-asset host blocked | step-0 probe; fallback codeload `dist` tag |
| NIM / W&B reject `response_format` schema | probe; fallback create + model_validate_json |
| Weave autopatch logs base64 video (slow, large) | postprocess_inputs; `WEAVE_DISABLED=true` in pod if traces >1 MB |
| basePath `/app` vs Ingress strip; StaticFiles slash redirects drop `/app` | `basePath` + `trailingSlash: true` + Link only; test on cluster at step 4 |
| ~300 MB wheels per pod start | initContainer, 600 s rollout; prebuilt image later |
| VastDB unreachable / duplicate rows | JSON flag; upsert in one tx |
| time | Landing, Boxes overlay, alerts "Mark as handled" cut first |

## Proposed rules
`.claude/rules/backend.md` (`paths: backend/**`) and `.claude/rules/web.md` (`paths: web/**`): one line per enforcement row naming its guard; registry watchlist rows: openapi-typescript (gate 3 idle, 2026-10-17); arq/Redis (deferred: scope, 2026-10-17).
