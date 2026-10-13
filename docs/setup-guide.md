# Setup guide (as actually run)

Cluster `ac-ws-dev-use2`, us-east-2, EKS v1.36.4, 5 × amd64 nodes, from a Mac (`bash`, `helm` v4.2.4, Docker Desktop).
Each step links to the log captured while running it. Errors and fixes: [troubleshooting.md](troubleshooting.md).

```bash
cp env.example .env && source .env
```

## Prerequisites check · [log 01](../logs/01-cluster-prerequisite-check.log)

```bash
kubectl get crd | grep actions.github.com     # empty -> ARC not installed
kubectl get storageclass                      # gp3 (default), EBS CSI running
aws eks describe-cluster --name $CLUSTER --region $REGION --query cluster.identity.oidc.issuer --output text
aws iam list-open-id-connect-providers        # issuer ID listed -> IRSA ready
```

## Step 0 · Install ARC · [logs 03](../logs/03-arc-controller-403-then-recovered.log), [04](../logs/04-arc-scale-set-install-and-runner-watch.log)

1. GitHub App **`ac-ws-arc-runners-dev`** on the personal account `@ajaychinthapalli`
   - Homepage URL: `https://github.com/actions/actions-runner-controller`
   - Webhook: inactive
   - **Repository permissions → Administration: Read & write**, Metadata: Read
   - Installed with access to `arc-runners-sandbox` (private repo)
2. `APP_ID=… INSTALLATION_ID=… PRIVATE_KEY_FILE=… bash manifests/arc/install-arc.sh`
3. Run `.github/workflows/ci.yml` from the Actions tab; `kubectl get pods -n arc-runners -w` shows a runner pod complete in ~9 s.

## Step 1 · Variables

Already in `.env`: `KAGENT_VERSION=0.10.3`, `BEDROCK_MODEL=us.anthropic.claude-sonnet-4-6`.

## Step 2 · Install kagent · [logs 05](../logs/05-kagent-install-controller-crashloop.log), [06](../logs/06-kagent-demo-agents-and-cleanup.log)

```bash
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
  --namespace kagent --create-namespace --version $KAGENT_VERSION
helm show values oci://ghcr.io/kagent-dev/kagent/helm/kagent --version $KAGENT_VERSION > kagent-values.yaml
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --namespace kagent --version $KAGENT_VERSION \
  -f kagent-values.yaml -f manifests/kagent/kagent-overrides.yaml
kubectl get pods -n kagent    # controller, kmcp, postgresql, tools, ui
```

Expect the controller to restart 1–2 times while PostgreSQL starts.

## Step 3 · Bedrock access via IRSA · [log 07](../logs/07-bedrock-access-denied-and-model-switch.log)

```bash
# 3a. Can the account call the model at all?
aws bedrock-runtime converse --region $REGION --model-id $BEDROCK_MODEL \
  --messages '[{"role":"user","content":[{"text":"Reply with OK"}]}]' \
  --query 'output.message.content[0].text' --output text        # -> OK

# 3b. IAM policy
envsubst < iam/bedrock-invoke.json.tmpl > bedrock-invoke.json
aws iam create-policy --policy-name arc-readiness-bedrock --policy-document file://bedrock-invoke.json

# 3c. ServiceAccount with IAM role
eksctl create iamserviceaccount --cluster $CLUSTER --region $REGION \
  --namespace kagent --name arc-readiness-agent \
  --attach-policy-arn arn:aws:iam::$ACCOUNT:policy/arc-readiness-bedrock --approve

# 3d. ModelConfig
kubectl apply -f manifests/kagent/bedrock-modelconfig.yaml
```

## Step 4 · Read-only Kubernetes tool server · [log 08](../logs/08-readonly-tool-server-connection-refused.log)

```bash
kubectl apply -f manifests/kagent/arc-k8s-readonly.yaml
kubectl get remotemcpserver arc-k8s-readonly -n kagent    # ACCEPTED True within ~60s

SA=system:serviceaccount:kagent:arc-k8s-readonly
kubectl auth can-i list autoscalingrunnersets.actions.github.com -A --as=$SA   # yes
kubectl auth can-i delete pods -n arc-runners --as=$SA                         # no
kubectl auth can-i get secrets -n arc-runners --as=$SA                         # no
```

## Step 5 · Build `arc-release-info` · [logs 09](../logs/09-docker-build-helm-404.log), [11](../logs/11-mcp-sdk-pin-and-rollout.log)

See [tools/arc-release-info/README.md](../tools/arc-release-info/README.md). Final image: `$ECR/arc-release-info:0.1.1`.

## Steps 6–7 · Deploy and register it · [logs 10](../logs/10-mcp-sdk-v2-module-not-found.log), [12](../logs/12-tool-servers-accepted-and-agent-ready.log)

```bash
envsubst < manifests/kagent/arc-release-info.yaml | kubectl apply -f -
kubectl logs -n kagent -l app=arc-release-info --tail=20     # "Uvicorn running on http://0.0.0.0:8080"
kubectl get remotemcpserver -n kagent                        # both ACCEPTED True
```

## Step 8 · Apply the agent · [log 12](../logs/12-tool-servers-accepted-and-agent-ready.log)

```bash
kubectl apply -f manifests/kagent/arc-upgrade-readiness-agent.yaml
kubectl get agents -n kagent                                 # READY True
kubectl logs -n kagent deploy/arc-upgrade-readiness | grep -E 'toolFilterCount|Bedrock'
```

## Step 9 · Test in the UI · [log 13](../logs/13-agent-first-run-tool-calls.log), [review](first-run-review.md)

```bash
kubectl -n kagent port-forward service/kagent-ui 8080:8080
# http://localhost:8080 -> arc-upgrade-readiness ->
# "Assess upgrading ARC from 0.14.2 to the latest gha-runner-scale-set release."
```

## Step 10 · Weekly report to Slack (pending)

Test the A2A call locally first, then apply [`cronjob-weekly-report.yaml`](../manifests/kagent/cronjob-weekly-report.yaml):

```bash
kubectl -n kagent port-forward svc/kagent-controller 8083:8083 &
curl -s --max-time 300 http://localhost:8083/api/a2a/kagent/arc-upgrade-readiness/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","messageId":"test-1","parts":[{"kind":"text","text":"Assess upgrading ARC to the latest gha-runner-scale-set release."}]}}}' \
  > a2a-response.json
jq -r '.result.artifacts[-1].parts[]? | select(.kind=="text") | .text' a2a-response.json
```

## Cleanup

```bash
kubectl delete -f manifests/kagent/arc-upgrade-readiness-agent.yaml
envsubst < manifests/kagent/arc-release-info.yaml | kubectl delete -f -
kubectl delete -f manifests/kagent/arc-k8s-readonly.yaml -f manifests/kagent/bedrock-modelconfig.yaml
helm uninstall kagent -n kagent && helm uninstall kagent-crds -n kagent
eksctl delete iamserviceaccount --cluster $CLUSTER --region $REGION --namespace kagent --name arc-readiness-agent
aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT:policy/arc-readiness-bedrock
helm uninstall arc-runner-set -n arc-runners && helm uninstall arc -n arc-systems
```
