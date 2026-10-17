#!/usr/bin/env bash
# Deploy SixthSense v1 to the team namespace as a SECOND deployment (`sixthsense-v1`) next to the
# old `sixthsense` one. Run ON THE LAB VM from the sixthsense/ folder:
#
#   bash deploy.sh <dist-sha>   # apply Secret/ConfigMap/Deployment/Service + Ingress /v1 -> sixthsense-v1
#   bash deploy.sh --cutover    # point the /app Ingress at sixthsense-v1 (old deployment kept)
#   bash deploy.sh --rollback   # point /app back at the old sixthsense deployment
#
# <dist-sha> is the commit printed by scripts/release.sh (orphan `dist` branch). The pod fetches
# codeload.github.com/<repo>/tar.gz/<sha>, so the SHA pins exactly what runs.
set -euo pipefail
CFG=$(ls /config/*.config | head -1)
get(){ grep "^$1=" "$CFG" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"; }
USERNAME=$(get USERNAME)
NS="$USERNAME"; export KUBECONFIG=/config/${NS}-k8s.yaml
APP_HOST="${APP_HOST:-video-lab-team-${USERNAME#team-}.cosmos.vastdata.com}"
OLD=sixthsense; APP=sixthsense-v1; PORT=8080
REPO="${REPO:-Dinesh-Sunny/sixthsense}"

point_app_ingress(){  # $1 = service name behind /app
  kubectl -n "$NS" patch ingress "$OLD" --type=json \
    -p "[{\"op\":\"replace\",\"path\":\"/spec/rules/0/http/paths/0/backend/service/name\",\"value\":\"$1\"}]"
  kubectl -n "$NS" get ingress "$OLD" -o jsonpath='{.spec.rules[0].http.paths[0].backend.service.name}'; echo
  sleep 3; curl -s "http://${APP_HOST}/app/healthz" || true; echo
}

case "${1:-}" in
  --cutover) point_app_ingress "$APP"; echo "/app now serves ${APP} (rollback: bash deploy.sh --rollback)"; exit 0 ;;
  --rollback) point_app_ingress "$OLD"; echo "/app back on ${OLD}"; exit 0 ;;
  "" | -h | --help) sed -n '2,11p' "$0"; exit 1 ;;
esac
SHA="$1"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "need the full 40-hex dist commit SHA"; exit 1; }

# Personal keys (MAPBOX_TOKEN, TFL_APP_KEY) live in a 0600 file on the VM, never in git or stdout.
if [ -f "$HOME/.config/sixthsense.env" ]; then set -a; . "$HOME/.config/sixthsense.env"; set +a; fi

# Secret from the team config. Values go through a 0600 temp file, never argv or stdout.
ENVF=$(umask 077; mktemp); trap 'rm -f "$ENVF"' EXIT
put(){ [ -n "$2" ] && printf '%s=%s\n' "$1" "$2" >> "$ENVF" || true; }
# Pods can't resolve the public lab hostname, so talk to the backend Service in-cluster.
put VSS_URL "${VSS_URL_IN_CLUSTER:-http://video-backend-service:8000}";put VSS_USERNAME "$USERNAME"; put VSS_PASSWORD "$(get PASSWORD)"
put GPU_BEARER_TOKEN "$(get GPU_BEARER_TOKEN)"; put GPU_HOST "$(get GPU_HOST)"
put COSMOS3_REASON_URL "$(get COSMOS3_REASON_URL)"; put YOLO_URL "$(get YOLO_URL)"
put WANDB_API_KEY "${WANDB_API_KEY:-$(get WANDB_API_KEY)}"; put WANDB_TEAM "${WANDB_TEAM:-$(get WANDB_TEAM)}"
put WANDB_PROJECT "${WANDB_PROJECT:-$(get WANDB_PROJECT)}"
put S3_ENDPOINT "$(get S3_ENDPOINT)"; put ACCESS_KEY "$(get ACCESS_KEY)"; put SECRET_KEY "$(get SECRET_KEY)"
put VASTDB_BUCKET "$(get VASTDB_BUCKET)"; put DISCORD_WEBHOOK_URL "${DISCORD_WEBHOOK_URL:-}"
put MAPBOX_TOKEN "${MAPBOX_TOKEN:-}"; put TFL_APP_KEY "${TFL_APP_KEY:-}"
kubectl -n "$NS" create secret generic ${APP}-env --from-env-file="$ENVF" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap ${APP}-boot --from-file=bootstrap.py=deploy/bootstrap.py \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NS" apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata: {name: ${APP}, labels: {app: ${APP}}}
spec:
  replicas: 1  # run state + single-flight lock live in memory (HPA needs arq/Redis first)
  selector: {matchLabels: {app: ${APP}}}
  template:
    metadata: {labels: {app: ${APP}}, annotations: {sixthsense/dist-sha: "${SHA}"}}
    spec:
      initContainers:
      - name: install
        image: python:3.12-slim
        command: ["python", "/boot/bootstrap.py", "install"]
        env: [{name: DIST_SHA, value: "${SHA}"}, {name: REPO, value: "${REPO}"}]
        volumeMounts: [{name: srv, mountPath: /srv}, {name: boot, mountPath: /boot}]
      containers:
      - name: app
        image: python:3.12-slim
        command: ["python", "/boot/bootstrap.py", "serve"]
        ports: [{containerPort: ${PORT}}]
        env:
        - {name: PORT, value: "${PORT}"}
        - {name: STORE_BACKEND, value: "${STORE_BACKEND:-vast}"}
        - {name: RUNS_ENABLED, value: "${RUNS_ENABLED:-true}"}
        envFrom: [{secretRef: {name: ${APP}-env}}]
        volumeMounts: [{name: srv, mountPath: /srv}, {name: boot, mountPath: /boot}]
        readinessProbe: {httpGet: {path: /readyz, port: ${PORT}}, initialDelaySeconds: 5, periodSeconds: 10, timeoutSeconds: 8}
        livenessProbe: {httpGet: {path: /healthz, port: ${PORT}}, initialDelaySeconds: 30, periodSeconds: 20}
        resources: {requests: {cpu: 250m, memory: 512Mi}, limits: {memory: 2Gi}}
      volumes:
      - {name: srv, emptyDir: {}}
      - {name: boot, configMap: {name: ${APP}-boot}}
---
apiVersion: v1
kind: Service
metadata: {name: ${APP}, labels: {app: ${APP}}}
spec: {selector: {app: ${APP}}, ports: [{name: http, port: 80, targetPort: ${PORT}}]}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${APP}
  annotations: {nginx.ingress.kubernetes.io/rewrite-target: /\$2, nginx.ingress.kubernetes.io/proxy-body-size: 50m}
spec:
  ingressClassName: nginx
  rules:
  - host: ${APP_HOST}
    http:
      paths:
      - {path: /v1(/|$)(.*), pathType: ImplementationSpecific, backend: {service: {name: ${APP}, port: {number: 80}}}}
YAML
kubectl -n "$NS" rollout status deploy/${APP} --timeout=600s
curl -s "http://${APP_HOST}/v1/healthz"; echo
curl -s "http://${APP_HOST}/v1/readyz"; echo
echo "Check http://${APP_HOST}/v1/api/incidents, then: bash deploy.sh --cutover"
