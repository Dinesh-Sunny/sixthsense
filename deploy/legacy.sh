#!/usr/bin/env bash
# LEGACY v0 deploy (stdlib app/ at /app). Kept for rollback redeploys; v1 uses ../deploy.sh.
# Run ON THE LAB VM from the sixthsense/ folder:  bash deploy/legacy.sh
set -euo pipefail
CFG=$(ls /config/*.config | head -1)
get(){ grep "^$1=" "$CFG" | cut -d= -f2- ; }
USERNAME=$(get USERNAME); INGRESS_URL=$(get INGRESS_URL); PASSWORD=$(get PASSWORD)
NS="$USERNAME"; export KUBECONFIG=/config/${NS}-k8s.yaml
APP_HOST="video-lab-team-${USERNAME#team-}.cosmos.vastdata.com"; APP=sixthsense; PORT=8080
BUILD=$(mktemp -d); cp app/main.py app/index.html app/incidents.json app/metrics.json pipeline/vss.py "$BUILD/"
du -sh "$BUILD"
kubectl -n "$NS" create configmap ${APP}-code --from-file="$BUILD" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create secret generic ${APP}-vss-creds \
  --from-literal=VSS_URL="$INGRESS_URL" --from-literal=VSS_USERNAME="$USERNAME" --from-literal=VSS_PASSWORD="$PASSWORD" \
  --from-literal=WANDB_API_KEY="${WANDB_API_KEY:-$(get WANDB_API_KEY)}" --from-literal=GPU_BEARER_TOKEN="$(get GPU_BEARER_TOKEN)" \
  --from-literal=DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata: {name: ${APP}, labels: {app: ${APP}}}
spec:
  replicas: 1
  selector: {matchLabels: {app: ${APP}}}
  template:
    metadata: {labels: {app: ${APP}}}
    spec:
      containers:
      - name: app
        image: python:3.12-slim
        ports: [{containerPort: ${PORT}}]
        env: [{name: PORT, value: "${PORT}"}]
        envFrom: [{secretRef: {name: ${APP}-vss-creds}}]
        volumeMounts: [{name: code, mountPath: /code}]
        workingDir: /code
        command: ["python", "main.py"]
        readinessProbe: {httpGet: {path: /health, port: ${PORT}}, initialDelaySeconds: 3, periodSeconds: 5}
      volumes: [{name: code, configMap: {name: ${APP}-code}}]
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
      - {path: /app(/|$)(.*), pathType: ImplementationSpecific, backend: {service: {name: ${APP}, port: {number: 80}}}}
YAML
kubectl -n "$NS" rollout restart deploy/${APP}
kubectl -n "$NS" rollout status deploy/${APP} --timeout=120s
curl -s "http://${APP_HOST}/app/health"; echo
echo "Open https://workshop.thecosmoslabs.com and click App"
