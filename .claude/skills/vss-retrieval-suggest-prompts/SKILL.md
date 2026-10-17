---
name: retrieval-suggest-prompts
description: >-
  Fetch AI-generated search prompt chips and key events via GET /api/v1/suggestions,
  produced by the prompt-suggester enrichment job from recent VastDB segments. Use to
  seed the search box with relevant example queries or surface notable recent events.
---

# Retrieval: suggest prompts (vss2)

Returns the latest batch of **search prompt suggestions** + **key events** the enrichment `prompt-suggester` computed from recent segments and wrote to VastDB (`vss-prompts-events`). Requires a JWT (`retrieval/login`).

## Request — `GET /api/v1/suggestions`

```bash
curl -s "$BACKEND/api/v1/suggestions" -H "Authorization: Bearer $TOKEN"
```

Content is ACL-filtered to the caller. Use the returned prompts as ready-to-run `query` strings for `retrieval/search`, and key events as highlights.

## Depends on the enrichment pipeline

These come from the scheduled `prompt-suggester` enrichment job writing to `vss-prompts-events`. If empty:
- The enrichment job may not have run yet.
- Lookback window found no new segments — logs show `[SUGGEST] No new videos in lookback window`.
- Check `retrieval/dashboard` that segments are actually being indexed.

## Agent instructions

1. Ensure a JWT.
2. Treat items as suggestions, not guarantees — feed prompts into `retrieval/search`.
3. If empty, check recent ingest (`retrieval/dashboard`) before assuming a bug.
