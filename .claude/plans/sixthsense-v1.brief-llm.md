# sixthsense-v1 brief: LLM + tracing (weave 0.53.12, openai 3.33.0)
Sources fetched 2026-10-17: coreweave weave docs (openai.md, ops.md, inference.md), NVIDIA NIM VLM 1.7.0 docs (cosmos-reason3/api.html, structured-generation.html), weave 0.53.12 and openai 3.33.0 wheel source ("src" below).

## weave + openai brief (v0.53.12 / 3.33.0) - APIs to use
- [must] `weave.init(f"{team}/{project}", postprocess_inputs=drop_media, settings={"print_call_link": False}, attributes={"app": "sixthsense"})`; wv-init. Sync + network: call `await asyncio.to_thread(weave.init, ...)` in lifespan, `weave.finish()` on shutdown (flushes). src: weave/trace/api.py:41.
- [must] Client-level `postprocess_inputs` runs after each op's own hook for EVERY op incl. autopatched openai spans (api.py init docstring; ops.md). This closes wv-gotcha-video; op-level hooks alone do not. `drop_media(inputs)`: walk `messages[*].content[*]`, replace `video_url.url` starting `data:` with `"<video {n} bytes>"`, bytes args with len. Pure fn, unit-tested.
- [must] Gate init on key: with no credentials `weave.init` calls `wandb.login(force=True)` (interactive; hangs/raises in pod) - src weave_init.py:345. Init only if `WANDB_API_KEY` set; wrap in try/except -> log + run untraced. Ops are plain functions when no client, so tests/JsonStore mode need no network.
- [must] Key route: weave reads `WANDB_API_KEY` env or netrc only (src wandb_interface/auth.py:272). Settings owns the `SecretStr`; `tracing.py` exports it with `os.environ.setdefault` before init (add per-file-ignore for the os.environ ban there, document why).
- [should] `@weave.op(kind=..., name=...)`: kind literals are agent|llm|tool|search|guardrail|scorer (lowercase; ops.md example "LLM" is wrong). run_mode=agent, watch=search, verify=tool, foresee=llm, selfcheck=llm (wv-op). Re-export as `op` from tracing.py.
- [should] `with weave.attributes({"mode":m,"run_id":r})` around run_mode, set BEFORE TaskGroup spawn (contextvar copied into tasks; wv-attributes). Inner values override outer.
- [adopt] Trace deep-link: inside foresee/selfcheck `c = weave.get_current_call(); c.ui_url` (src weave/trace/call.py:140) -> optional `trace_url` on Incident for "See how it decided". Store only when set; None when untraced.
- [must] Clients: one `AsyncOpenAI` per upstream in lifespan, `await client.close()` on exit (oa-asyncclient). Pass `timeout=120.0` (float): avoids importing httpx2 (oa-asyncclient note). `max_retries=2`; do NOT wrap openai calls in tenacity (retries multiply; oa-retries covers 408/409/429/5xx/connect).
- [must] W&B Inference: `base_url="https://api.inference.wandb.ai/v1"`, `project="<team>/<project>"` identical to weave.init, model `meta-llama/Llama-3.3-70B-Instruct` (inference.md, wv-inference-trace). 429 "Concurrency limit reached" -> keep `Semaphore(gpu_concurrency)` below cap; keep it for W&B calls separately (cap is per user+project).
- [must] Cosmos video call: content part `{"type":"video_url","video_url":{"url":"data:video/mp4;base64,..."}}` (or http URL) per NIM api.html. Frame control via `extra_body={"media_io_kwargs":{"video":{"num_frames":16}}}`; fps and num_frames are mutually exclusive, fps above the clip's true fps -> 400, default 4 fps, best at <=16k mm tokens. Prefer `num_frames`. Put in `modes.py` constants. Pre-resolve model id once from `/v1/models` (as old models.py:44).
- [must] JSON output (oa-parse): NIM VLM doc supports `response_format={"type":"json_schema","json_schema":{"name":..,"schema":Forecast.model_json_schema()}}` / `parse`; Cosmos3-Reason page and W&B Inference page do NOT document it. Probe once at step 0 (`sixthsense probe` prints supported? y/n per endpoint, never values); fallback `create` + `Forecast.model_validate_json(extract_json(text))` (keep think-strip). Never combine guided JSON with the `<think>…</think><answer>` prompt: pick no-think+schema OR think+extract_json per endpoint.
- [should] `max_tokens` high enough for reasoning (NIM: 256-1024 simple, up to 4096 with think); truncated JSON otherwise; parse raises `LengthFinishReasonError` -> map to `unknown` state (code-style: unknown, not raise).
- [should] Errors: catch `openai.APIStatusError` (use `.request_id`, `.status_code`), `APITimeoutError`, `RateLimitError` in clients/models.py only; surface as one `UpstreamError` to pipeline.

## Plan corrections
- [must] Risks/Library rows: "postprocess_inputs on the wrapping op" is insufficient (autopatched openai spans still log raw inputs, wv-gotcha-video) -> client-level `weave.init(postprocess_inputs=...)` + a test that feeds a data URL through `drop_media`. WEAVE_DISABLED fallback stays.
- [must] Library row "tracing: weave.init only if key set" -> also needs the key->env bridge and try/except above; weave.init is blocking so `to_thread`.
- [must] Library row LLM/VLM: `httpx2.Timeout(120)` -> `timeout=120.0` (no httpx2 importer, no new ruff ban); add `extra_body` media_io_kwargs; Cosmos `max_retries=2` not tenacity.
- [should] Pipeline flow: W&B judge JSON via same probe-gated path (old code used `json_object` at models.py:77); keep `temperature=0`.
- [should] facts: add "autopatch only logs client base_url+version, not api_key" (src openai_sdk.py:379) so key leakage is not a risk; but never pass Settings/SecretStr as an op argument.

## Opportunities
- [adopt] observability: wv-attributes + ui_url -> `Incident.trace_url` (contracts.py, Detail "See how it decided").
- [adopt] reliability: wv-semaphore pattern (single shared client + Semaphore) -> pipeline.py; uses plain Semaphore now, `WEAVE_PARALLELISM` only matters with Evaluation (later).
- [later] testing: wv-evaluation + wv-scorer-class (kind "scorer"): self-check accuracy as Scorer over stored incidents; needs dataset of clips.
- [later] observability: `with weave.thread(run_id)` groups a run's ops as one thread (wv-thread); cheap, skip until demo works.
- [later] reuse: oa-raw `with_raw_response` for x-request-id / rate-limit headers when debugging 429s.

## Proposed rules
- `weave`, `openai`, `httpx2` importable only from tracing.py / clients/models.py: ruff TID251 + per-file-ignores (already planned) + conventions test.
- Every pipeline step function is decorated by `tracing.op` (not `weave.op`): convention test walks `pipeline.py` for `__wrapped__`/op attribute.
- `drop_media` test: data URL and bytes never survive; guard = pytest.
- No `os.environ` outside settings.py except tracing.py key bridge: TID251 per-file-ignore, one line comment why.

## Outline updates
- wv-init: add `postprocess_inputs`, `postprocess_output`, `attributes` (replaces deprecated `global_*`), `settings={...}` (print_call_link, implicitly_patch_integrations, capture_code, redact_pii, http_timeout...; all also `WEAVE_<NAME>` env); `autopatch_settings` deprecated -> use `implicitly_patch_integrations=False` + `weave.integrations.patch_openai()`. Note: no credentials -> interactive `wandb.login`; key from `WANDB_API_KEY` env/netrc; `weave.finish()` flushes. (src 0.53.12)
- wv-op: kind literals agent|llm|tool|search|guardrail|scorer; `name=`, `color=`; client-level hook runs after op-level hook and covers autopatched ops. `Call.ui_url`, `weave.get_current_call()`.
- wv-openai-autopatch: patches Completions/AsyncCompletions create+parse and beta parse; logs client base_url+version only (no api_key); labels W&B Inference calls "Serverless Inference: <model>".
- wv-gotcha-video: replace note with client-level postprocess_inputs fix (verified in source, untested live).
- oa-parse / new entry nim-video-input: NIM Cosmos3 `video_url` data/http URL; `extra_body media_io_kwargs.video.{fps|num_frames}`; fps>actual -> 400; <=16k mm tokens; reasoning via prompt `<think>/<answer>` format; structured output not documented for Cosmos3, `response_format json_schema` documented for NIM VLM generic (docs.nvidia.com/nim/vision-language-models/1.7.0/structured-generation.html).
- Usage statuses: wv-init, wv-op, wv-attributes, wv-openai-autopatch, wv-inference-trace, oa-asyncclient, oa-retries, oa-parse -> adopt; wv-gotcha-video -> adopt (fixed via init hook); wv-semaphore -> adopt (plain Semaphore); wv-evaluation, wv-scorer-class, wv-thread, oa-raw -> later.
