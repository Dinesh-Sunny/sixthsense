---
paths:
  - "**/migrations/**"
  - "**/schema.*"
  - "**/*.sql"
  - "{prisma,drizzle,convex,db}/**"   # TODO(stub): keep only the real one
---
<!-- last-verified: 2026-10-01 -->
# Database

- Schema changes go through migrations (MIGRATION_TOOL). Never edit applied migrations.
- Migrations must be backward compatible with the currently deployed code (expand → migrate → contract).
- Every foreign key and frequent filter column gets an index. Justify any missing one.
- No destructive migration (drop/rename column/table) without explicit user approval.
- Seed data lives in SEED_PATH. Never point local tooling at production.
