---
name: deploy-health
description: >-
  Verify the VSS retrieval deployment is healthy — kubectl get pods, backend /health (8000),
  and GET /api/v1/config for effective backend settings. Use after deploying or when the
  UI/API is failing, to confirm pods are up and configured correctly.
---

# Deployment: health (vss2)

Confirms pods are running and the backend is wired correctly. Read-only.

## Pods / rollout

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
NS=$(grep '^USERNAME=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)   # e.g. team-1
export KUBECONFIG=/config/${NS}-k8s.yaml                     # e.g. /config/team-1-k8s.yaml
kubectl get pods -n <namespace>
kubectl get all -n <namespace>
kubectl describe pod -n <namespace> -l app=video-backend      # events on CrashLoop/ImagePull
kubectl rollout status deploy/video-backend -n <namespace>
```

Apps: `video-backend`, `video-frontend`, `video-batch-sync`.

## Probes

```bash
kubectl port-forward -n <namespace> deploy/video-backend 8000:8000 &
curl -s localhost:8000/health          # backend liveness/readiness
curl -s localhost:8000/                 # root
```

Via ingress: `curl -s http://video-lab.<cluster>.vastdata.com/api/v1/...`.

## Effective backend config — `GET /api/v1/config`

Confirms what the backend actually loaded from the mounted secret (JWT required — `retrieval/login`):

```bash
curl -s "http://video-lab.<cluster>.vastdata.com/api/v1/config" -H "Authorization: Bearer $TOKEN"
```

Check S3 endpoint, `vdb_collection: vss-collection`, embedding host + `256` dims, Cosmos host — must match ingest. Compare `/config/vss-cli-secret.yaml` and `/config/backend-secret.yaml`; if either is missing and needed, ask the user to place it under `/config/`. Do not search the repo's `team-configs/`. Note the VastDB endpoint is expected to **differ**: backend `vdb_endpoint` = Query Engine VIP (reads), ingest `vdbendpoint` = regular data VIP (writes).

## Common failures

| Symptom | Check |
|---------|-------|
| Backend CrashLoop at start | `jwt_secret` empty (backend refuses to start) → fix secret, `rollout restart` |
| `ImagePullBackOff` | wrong image tag/registry in deployment YAML |
| Login 401 | `vast_host`/`tenant_name` wrong in secret |
| Search returns nothing | embedding host/dims or VastDB endpoint mismatch vs ingest (see `/api/v1/config` + `retrieval/dashboard`) |
| Ingress unreachable | ingress IP pending / DNS or ingress issue |

## Agent instructions

1. Resolve team from `/config/*.config` (`USERNAME`, e.g. `team-1`) and set `KUBECONFIG=/config/${USERNAME}-k8s.yaml`; if missing, ask the user to put it there. Run `kubectl get pods` first; `describe`/`logs` any non-Running pod.
2. Hit `/health`; then `GET /api/v1/config` to confirm wiring.
3. Cross-check `/api/v1/config` against `/config/vss-cli-secret.yaml` and `/config/backend-secret.yaml` when present; for deeper debugging read pod logs.
