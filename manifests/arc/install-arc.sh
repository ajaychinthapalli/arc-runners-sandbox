#!/usr/bin/env bash
# Install ARC (gha-runner-scale-set) for a PERSONAL GitHub account.
# Prereq: GitHub App "ac-ws-arc-runners-dev" installed on the account with
#   Repository permissions -> Administration: Read & write, Metadata: Read
#   (the org-level "Self-hosted runners" permission does nothing on a personal account)
# and with access to the arc-runners-sandbox repo.
set -euo pipefail
: "${ARC_VERSION:?source env.example first}"

APP_ID="${APP_ID:?set APP_ID}"
INSTALLATION_ID="${INSTALLATION_ID:?set INSTALLATION_ID}"
PRIVATE_KEY_FILE="${PRIVATE_KEY_FILE:?path to the app .pem}"

# 1. Controller
helm install arc oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
  --namespace arc-systems --create-namespace --version "$ARC_VERSION"

# 2. GitHub App secret
kubectl create namespace arc-runners --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic arc-github-app -n arc-runners \
  --from-literal=github_app_id="$APP_ID" \
  --from-literal=github_app_installation_id="$INSTALLATION_ID" \
  --from-file=github_app_private_key="$PRIVATE_KEY_FILE"

# 3. Runner scale set (repo-level: personal accounts cannot have account-wide runners)
helm install arc-runner-set oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --namespace arc-runners --version "$ARC_VERSION" \
  --set githubConfigUrl=https://github.com/ajaychinthapalli/arc-runners-sandbox \
  --set githubConfigSecret=arc-github-app \
  --set minRunners=0 --set maxRunners=3

# 4. Verify: controller + listener pods
kubectl get pods -n arc-systems
kubectl get autoscalingrunnerset -n arc-runners
kubectl get autoscalinglistener -n arc-systems
# Then run .github/workflows/ci.yml from the Actions tab and watch:
#   kubectl get pods -n arc-runners -w
