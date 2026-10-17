---
name: data-model
description: Design or change a data model (tables, collections, jsonb documents, graph edges, indexes, migrations) in the main session. Use before adding or altering schema or writing a migration.
when_to_use: Trigger phrases - "new table", "add a column", "model X", "schema for", "migration for", "store X". Skip for queries that don't change schema.
argument-hint: <what data to model or change>
arguments: [goal]
effort: high
---
<!-- last-verified: 2026-10-03 -->
# Data model: $goal

Runs in the main session so the design and the implementation share context. For an independent review afterwards, run `/data-review`.

## Context first
1. Read the data map: `.claude/agent-memory/data-architect/MEMORY.md` (stores, owners, conventions, commands). Missing or stale? Rebuild it from the code and update it.
2. Read the data rules in `.claude/rules/` and the data topics in `docs/knowledge/README.md` that the change touches, plus related `docs/adr/`.
3. Map the current model from real files: schema modules, applied migrations, CMS collections. Never invent a table, column, or helper; cite `path:line`.
4. Restate the need as access patterns: entities, cardinality, every read and write path, volume and growth, retention, tenant scope, personal data.

## Design checklist
- **Store**: pick the owner per the data map (relational table, jsonb document, graph edges, CMS collection, cache, queue). Relational by default; justify anything else.
- **Keys**: time-ordered ids for internal rows, random ids for anything users see or that acts as a secret. Natural keys become unique constraints, not primary keys.
- **Integrity**: the database enforces invariants: NOT NULL, FKs with a deliberate ON DELETE, UNIQUE, CHECK, exclusion constraints. App-only validation is a gap you name.
- **Indexes**: one per access pattern, tied to the query it serves; composite order follows equality → range → sort.
- **Index coverage**: every FK and frequent filter is indexed. Name each index you skip and why.
- **Tenancy and access**: tenant id on every tenant-owned row and inside its unique keys; state who may read and write each table.
- **Personal data**: classify fields; wire export, erasure, and retention; keep personal data out of logs and audit rows.
- **Time and history**: timezone-aware timestamps; decide hard delete, soft delete, versioning, or audit trail per entity.
- **Scale**: estimate rows at 1 and 3 years; plan partitioning, batched deletes, and archiving before they are urgent.

## Migration plan
- Expand → migrate → contract: each deploy must work with the code already running.
- Avoid long locks: add nullable columns, then backfill in batches, then validate constraints separately (`NOT VALID` → `VALIDATE`). Name any step that rewrites a table.
- Destructive steps (drop, rename, type change) need explicit user approval; stop and ask.
- Use the exact generate and apply commands from the data map.

## Verify
- Prove claims cheaply on the local dev database (`\d`, `EXPLAIN (ANALYZE, BUFFERS)` in a rolled-back transaction or a scratch database). Never touch shared or production databases.
- Check version-specific features against current docs, not memory.

## Output, then implement
1. **Summary** in three lines, then **access patterns**: query → frequency → index that serves it.
2. **Model**: ORM or DDL sketch in the project's style, with constraints.
3. **Options** only when a real choice exists: 2-3 with cost, risk, reversibility.
4. **Migration plan**: ordered steps, each safe to deploy alone, with rollback.
5. **Risks and open questions**. Ask the user only what blocks the work.
6. Durable decision → ADR draft in `docs/adr/NNNN-<title>.md`.
After the user agrees, implement in this session. New store, convention, or pitfall learned → update the data map.
