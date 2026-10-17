---
name: deploy-retrieval
description: >-
  Deploy the VSS retrieval stack (backend, frontend, batch-sync) to Kubernetes
  with QUICK_DEPLOY.sh <namespace> <cluster>, including building/pushing images.
  Use /config/team-<num>-k8s.yaml. Use to stand up or redeploy the retrieval side after build-yamls.
---

# Deployment: deploy retrieval (vss2)

Applies everything in `deployments/vss-k8s-application/` to the cluster. Prereq: `deploy-build-yamls` (secret + image tags), and `/config/team-<num>-k8s.yaml`.

## 1. Build & push images (if changed)

Build/push `vss-video-backend`, `vss-video-frontend`, `vss-video-batch-sync` from `source-code/retrieval/*` and `source-code/video-batch-sync` for `linux/amd64`, then set those tags in the deployment YAMLs (`deploy-build-yamls`).

## 2. Run QUICK_DEPLOY

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
NS=$(grep '^USERNAME=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)   # e.g. team-1
export KUBECONFIG=/config/${NS}-k8s.yaml                     # e.g. /config/team-1-k8s.yaml
kubectl cluster-info
cd deployments/vss-k8s-application
./QUICK_DEPLOY.sh <namespace> <cluster_name>     # e.g. ./QUICK_DEPLOY.sh vastvideo v1234
```

**Secret:** use `/config/backend-secret.yaml`. If missing, ask the user to put it there, then copy it into `deployments/vss-k8s-application/backend-secret.yaml` for `QUICK_DEPLOY.sh`. Do not search the repo's `team-configs/` or invent secret values.

Steps it runs (fails fast if `backend-secret.yaml` is missing in the deploy dir):
1. create/label namespace (`zarf.dev/agent=ignore`)
2. apply `backend-secret.yaml` (subs `NAMESPACE`)
3. backend (+ service + `/api` ingress)
4. frontend (+ ingress)
5. batch-sync

It substitutes `NAMESPACE`/`CLUSTER_NAME` into each manifest and prints `kubectl get all` + the ingress IP.

## 3. Ingress DNS

```bash
kubectl get ingress -n <namespace>      # if IP was "pending"
```

Then open `http://video-lab.<cluster>.vastdata.com` and log in with VAST credentials.

## Redeploy / update

Re-run `QUICK_DEPLOY.sh` (idempotent `kubectl apply`), or:

```bash
kubectl set image deploy/video-backend backend=your.registry/vss-video-backend:v2 -n <namespace>
kubectl rollout restart deploy/video-backend -n <namespace>   # e.g. to reload the secret
kubectl rollout status deploy/video-backend -n <namespace>
```

## Notes

- This is retrieval only; for archive ingest use `ingest/upload-video` or `ingest/reingest-videos`.
- Backend ingress caps body at 110m; upload cap also via `max_upload_size_mb`.

## Agent instructions

1. Resolve team from `/config/*.config` (`USERNAME`, e.g. `team-1`) and set `KUBECONFIG=/config/${USERNAME}-k8s.yaml`; if missing, ask the user to place it there. Confirm `kubectl cluster-info`.
2. Confirm images are pushed and `/config/backend-secret.yaml` exists (ask user to add it if not).
3. Ensure deploy dir has `backend-secret.yaml` copied from `/config/backend-secret.yaml`.
4. Run `QUICK_DEPLOY.sh <ns> <cluster>`; capture the ingress IP and verify with `deploy-health`.
5. On failures, inspect pod logs (`kubectl logs -l app=<app> -n <ns>`) and `deploy-health`.
