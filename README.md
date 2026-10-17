# SixthFrame - the sixth sense your cameras were missing

Built at the VAST Builders Challenge (London, 17 Oct 2026). A video agent that watches highway and street
CCTV, **verifies** risky moments with YOLO boxes, asks **NVIDIA Cosmos Reason** what happens next and why,
then **checks its own prediction** against the next clip - so it reports a measured accuracy, not a claim.

## How it works
```
VSS search (VastDB hybrid index) ─▶ Verify (YOLO11 boxes: closing gap) ─▶ Foresee (Cosmos3-Reason on the clip)
      ─▶ Self-check (W&B LLM judge vs next segment) ─▶ incidents.json ─▶ web app (cards, alerts, ask the footage)
                                   every step traced with W&B Weave
```
| Step | Code | Stack |
|---|---|---|
| Watch | `pipeline/run.py: watch` | VSS `/search` over VastDB (Cosmos Embed1 vectors) |
| Verify | `run.py: verify` | YOLO11 detections sidecar or `/v1/infer` |
| Foresee | `run.py: foresee` | Cosmos3-Reason, clip sent inline |
| Self-check | `run.py: selfcheck` | next segment of the same video + W&B inference judge |
| Show / act | `app/` | stdlib Python server, one HTML page, alerts + Discord webhook |

## Run (on the lab VM)
```bash
python3 pipeline/probe.py                    # check every API, print JSON shapes
python3 pipeline/run.py --mode road --limit 12
python3 pipeline/run.py --mode street --limit 12
bash deploy.sh                               # K8s, Ingress /app -> workshop.thecosmoslabs.com -> App
```
Optional: `pip install weave` for traces. Flags: `VERIFY_MODE=boxes|cosmos`, `FORESEE_VIA=direct|text`, `LLM_MODEL=<W&B model id>`.

## Team
Dinesh Sunny
