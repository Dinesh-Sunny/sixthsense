---
name: project-conventions
description: Domain glossary and business rules for this project. Load when working on domain logic, naming domain entities, or when unfamiliar business terms appear.
user-invocable: false
metadata:
  owner: "{{TEAM_OR_PERSON}}"
  last-reviewed: "{{YYYY-MM-DD}}"
---

# Project conventions & domain knowledge

<!-- Background knowledge: Claude loads it when relevant, and it is hidden from the / menu. -->

## Glossary
| Term | Meaning | Code name |
| --- | --- | --- |
| {{TERM}} | {{DEFINITION}} | `{{IdentifierInCode}}` |

## Business rules
- {{RULE_1 e.g. "An invoice is immutable once status = sent"}}

## Domain invariants
- {{INVARIANT}}

See [reference.md](reference.md) for detailed entity relationships.
