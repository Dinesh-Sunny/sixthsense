# SixthSense

Video agent that predicts what happens next on CCTV, verifies it with YOLO boxes, and grades its own predictions against the next clip. Built at the VAST Builders Challenge (London, 17 Oct 2026).

## Stack

- Language: Python 3.12, standard library only in `app/` (the pod has no pip step)
- Framework: none - `http.server` app + one static `index.html`
- Package manager: pip only for optional tooling (`weave`); never required to run
- Database / ORM: VAST VastDB via the VSS backend API (`/api/v1`); results in `app/incidents.json`
- Styling / UI: hand-written CSS in `app/index.html`
- Testing: `python3 pipeline/probe.py` (live API smoke test), `python3 -m py_compile`
- Hosting / CI: team Kubernetes namespace on the VAST lab cluster, Ingress `/app` (`deploy.sh`)

## Commands

| Task | Command |
| --- | --- |
| Install | none (optional: `pip install weave`) |
| Dev server | `PORT=8080 python3 app/main.py` |
| Build | none |
| Lint | `python3 -m py_compile app/*.py pipeline/*.py` |
| Format | none |
| Type-check | none |
| Test (all) | `python3 pipeline/probe.py` |
| Test (one file) | `python3 -m py_compile <path>` |
| E2E | `python3 pipeline/run.py --mode road --limit 3` |
| DB migrate | none |

Before calling a task done, run the compile check and, on the lab VM, `probe.py`.

## Architecture

- Layout: `pipeline/` (watch, verify, foresee, self-check, store), `app/` (web server + page + JSON data), `docs/` (architecture, knowledge)
- Entry points: `pipeline/run.py`, `pipeline/probe.py`, `app/main.py`, `deploy.sh`
- Data flow: VSS search -> YOLO closing-gap check -> Cosmos3-Reason JSON forecast -> LLM judge vs next segment -> `app/incidents.json` -> web app
- External services: VSS backend (JWT), Cosmos3-Reason + YOLO11 GPU endpoints (bearer), W&B serverless inference + Weave
- Copy context: `VOICE.md` (voice, tone, vocabulary, claims policy). All user-facing words follow it
- Hackathon reference repo: `../reference-vast-builders-challenge/` (skills describe every API)
- Deep dives live in `docs/knowledge/`. See its README index; load only what the task needs.

## Conventions

- Read existing code before writing; follow nearby patterns, naming, and structure.
- Keep `app/` flat and stdlib-only: it ships as a Kubernetes ConfigMap (about 1 MiB limit).
- Use relative URLs in `index.html`; the app is served under `/app`.
- Tolerate unknown API shapes with `first()` key lookups; record real shapes from `probe.py` output.
- Only show numbers measured in a real run; label fixture data as fixture.
- Comment *why*, not *what*; match the surrounding comment density.

## Workflow

- Hackathon day: commit straight to `main` in small steps; keep README current for judges.
- Conventional Commits.
- Never commit secrets, `.env*`, clips or probe dumps.

## Do not

- Edit generated files: `GEMINI.md`, `context-pack*.md`, `.github/copilot-instructions.md`, `.cursor/rules/`.
- Touch the shared DataEngine pipeline or other teams' namespaces.
- Print or log `/config` values, JWTs or bearer tokens.
- Run destructive commands without explicit confirmation.

## Environment

- Required env var names are in `.env.example`. Never read or print secret values.
- Local services: none; everything runs against the lab VM's endpoints.

## Knowledge upkeep

- Record new lessons in `.claude/inbox.md` (one line each); never append to this file directly.
- This file has a hard budget. When it's full, demote detail to `docs/knowledge/` and leave a one-line pointer.
