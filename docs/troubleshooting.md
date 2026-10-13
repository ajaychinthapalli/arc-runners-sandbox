# Errors and fixes

Every problem hit while building the agent, in order. Raw output for each is in [`../logs`](../logs).

| # | Symptom | Root cause | Fix | Log |
| --- | --- | --- | --- | --- |
| 1 | No `arc-systems` / `arc-runners` namespaces, no `actions.github.com` CRDs | ARC was never installed on this cluster | Install ARC (Step 0 in the setup guide) | [01](../logs/01-cluster-prerequisite-check.log), [02](../logs/02-initial-cluster-state.log) |
| 2 | GitHub App "Self-hosted runners" permission has no effect | That permission is org-only; the app is on a personal account | Repo permission **Administration: Read & write**, scale set `githubConfigUrl` points at the repo | – |
| 3 | `403 Forbidden ... Resource not accessible by integration` on `.../actions/runners/registration-token` | First reconcile ran before the new Administration permission took effect | None needed: retry 21s later registered scale set id 1 | [03](../logs/03-arc-controller-403-then-recovered.log) |
| 4 | `kagent-controller` CrashLoopBackOff | Controller starts before bundled PostgreSQL is ready (runs migrations on start) | None needed: healthy after 2 restarts | [05](../logs/05-kagent-install-controller-crashloop.log) |
| 5 | 10 demo agents in `CreateContainerConfigError` | Installed with full default values; demo agents reference a provider API key secret that doesn't exist | `helm upgrade ... -f kagent-overrides.yaml` | [06](../logs/06-kagent-demo-agents-and-cleanup.log) |
| 6 | Bedrock `AccessDeniedException: anthropic.claude-sonnet-5-5 is not available for this account` | `agreementAvailability: NOT_AVAILABLE`; after accepting it in all 3 US regions the call was still denied (propagation or account gating) | Switched to `us.anthropic.claude-sonnet-4-6` (returned `OK`) | [07](../logs/07-bedrock-access-denied-and-model-switch.log) |
| 7 | `RemoteMCPServer arc-k8s-readonly` `ACCEPTED False`, controller log `connect: connection refused` | Startup race: controller reconciled ~ms before the server listened | None needed: next 60s reconcile registered 126 tools | [08](../logs/08-readonly-tool-server-connection-refused.log) |
| 8 | Docker build: `curl: (22) ... 404`, `gzip: stdin: unexpected end of file` | `HELM_VERSION` left as placeholder `v3.x.y` | `--build-arg HELM_VERSION=$(helm version --short \| cut -d+ -f1)` | [09](../logs/09-docker-build-helm-404.log) |
| 9 | `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | Unpinned `mcp[cli]` installed SDK 2.x, which renamed FastMCP | Pin `"mcp[cli]<2"`, rebuild as `0.1.1`, `kubectl set image` | [10](../logs/10-mcp-sdk-v2-module-not-found.log), [11](../logs/11-mcp-sdk-pin-and-rollout.log) |
| 10 | After rollout, logs still show the old traceback | `kubectl logs deploy/...` picked the old pod ("Found 2 pods") | `kubectl logs -n kagent -l app=arc-release-info` | [11](../logs/11-mcp-sdk-pin-and-rollout.log), [12](../logs/12-tool-servers-accepted-and-agent-ready.log) |
| 11 | First report: ":latest image likely behind v2.338.0" and "check your values" | Model guessed instead of verifying | Prompt rules in the agent's `systemMessage` | [first-run-review](first-run-review.md) |
| 12 | Report's upgrade commands use `oci://…/gha-rs-controller` and `…/gha-rs-runner-scale-set` | Agent built chart paths from the short `helm.sh/chart` labels (`gha-rs-controller-0.14.2`, `gha-rs-0.14.2`) | Real paths: `gha-runner-scale-set-controller`, `gha-runner-scale-set`; rule added | [report](../reports/2026-10-12-arc-0.14.2-to-0.15.0.md), [14](../logs/14-agent-full-report-ui-export.log) |
| 13 | Report pins the runner with `--set template.spec.containers[0].image=…` | `--set` on a list item replaces the item, dropping `name` and `command` | Values file with the full container spec; rule added | [report](../reports/2026-10-12-arc-0.14.2-to-0.15.0.md#corrected-upgrade-commands-human-reviewed) |
| – | `kubectl get pv pvc` → NotFound | Syntax: space instead of comma | `kubectl get pv,pvc -A` | [02](../logs/02-initial-cluster-state.log) |
| – | Bedrock status loop "Stopped" | Ctrl+Z suspends a job | Ctrl+C, or `kill %4` | [07](../logs/07-bedrock-access-denied-and-model-switch.log) |

## Details

### ARC 403 on a personal-account GitHub App

```
failed to get runner registration token (403 Forbidden): : Resource not accessible by integration
```

Repo-level runners need the **repository** permission *Administration: Read & write*. After changing app permissions, the owner must accept them on the installation page (**Settings → Applications → Installed GitHub Apps**). The controller retries on its own; the next reconcile created the scale set and listener.

### Bedrock model access, step by step

```bash
aws bedrock get-foundation-model-availability --region us-east-2 --model-id anthropic.claude-sonnet-5-5
```

| Field | Value seen | Meaning |
| --- | --- | --- |
| `authorizationStatus` | AUTHORIZED | Anthropic use-case form already done |
| `entitlementAvailability` | AVAILABLE | Account can subscribe |
| `agreementAvailability` | NOT_AVAILABLE → PENDING → AVAILABLE | Accepted with `create-foundation-model-agreement` |
| `regionAvailability` | AVAILABLE | Model is in the region |

A `us.` inference profile routes to us-east-1, us-east-2 and us-west-2, so check all three. If everything is `AVAILABLE` and calls still fail with "not available for this account", give it ~15 minutes, check **AWS Marketplace → Manage subscriptions**, then open an AWS Support case. Error text "not available for this account" is account-level, not an IAM policy problem.

### Startup race between kagent controller and a new MCP server

`ACCEPTED False` right after `kubectl apply` usually means the controller tried before the pod listened. Force a retry instead of waiting:

```bash
kubectl annotate remotemcpserver <name> -n kagent reconcile=$(date +%s) --overwrite
```

### Python MCP SDK 2.x

The SDK's own error message names the two options: migrate to `MCPServer`, or pin `mcp<2`. We pinned. Also note `FastMCP` binds to localhost by default; `host="0.0.0.0"` is required inside a pod.
