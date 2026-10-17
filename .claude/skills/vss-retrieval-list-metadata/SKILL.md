---
name: retrieval-list-metadata
description: >-
  Discover filterable fields and their values for VSS search via GET /api/v1/metadata/schema,
  /metadata/values, and /metadata/ingest-config. Use to resolve valid metadata_filters keys,
  autocomplete values (locations, cameras, capture types, tags), or list ingest field options
  before searching or uploading.
---

# Retrieval: list metadata (vss2)

Powers dynamic filters. Use it to turn a user's words into valid `metadata_filters` for `retrieval/search`. There are **no** dedicated `/tags`, `/locations`, or `/extra-metadata` routes — everything flows through these three.

## Filterable schema — `GET /api/v1/metadata/schema` (JWT)

Returns the filterable columns of `vss-collection` with type, label, `ui_type` (`select` if ≤100 distinct values, with `options`; else `text`).

```bash
curl -s "$BACKEND/api/v1/metadata/schema" -H "Authorization: Bearer $TOKEN"
# { "schema": [ {"name":"location","type":"string","ui_type":"select","label":"Location","options":[...]}, ... ], "table":"vss-collection" }
```

Internal columns (`pk`, `vectors`, `vectors_visual`, `source`, `reasoning_content`, `perception_json`, timing, `tags`, `is_public`, …) are **excluded** and can't be filtered here.

## Field values / autocomplete — `GET /api/v1/metadata/values` (JWT)

```bash
curl -s "$BACKEND/api/v1/metadata/values?field=location&prefix=War&limit=50" -H "Authorization: Bearer $TOKEN"
# { "field":"location", "values":["Warehouse A","Warehouse B"], "count":2 }
```

Params: `field` (required, must be a filterable column), `prefix` (optional), `limit` (default 50). Non-filterable/excluded fields → 400.

## Ingest field catalog — `GET /api/v1/metadata/ingest-config` (public, no auth)

Canonical options for ingest metadata (scenarios, capture types, labels). Use this
to populate metadata overrides in `ingest/reingest-videos`.

```bash
curl -s "$BACKEND/api/v1/metadata/ingest-config"
```

## Typical flow

1. `GET /metadata/schema` → which keys are filterable + their `options`.
2. For `text` fields, `GET /metadata/values?field=…&prefix=…` to resolve the exact value.
3. Build `metadata_filters` and call `retrieval/search`.

## Agent instructions

1. Always resolve `metadata_filters` keys/values against `schema`/`values` before searching — don't guess column names.
2. `ingest-config` is for **ingest** metadata; `schema`/`values` are for **search** filters. Don't cross them.
3. Tags aren't in the filter schema — pass them via the search `tags` array (values seen in results/dashboard).
