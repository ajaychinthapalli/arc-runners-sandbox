# Raw logs

Terminal output captured while building the ARC Upgrade Readiness Agent on `ac-ws-dev-use2` (us-east-2) on 2026-10-12.
Files are numbered in the order things happened. The AWS account ID, OIDC provider IDs and a Bedrock offer token are redacted.

| # | File | What it shows | Outcome |
| --- | --- | --- | --- |
| 01 | [01-cluster-prerequisite-check.log](01-cluster-prerequisite-check.log) | CRDs, Helm releases, pods, storage, OIDC provider | ARC missing; gp3 + EBS CSI + IRSA ready |
| 02 | [02-initial-cluster-state.log](02-initial-cluster-state.log) | Namespaces, nodes (v1.36.4), `kubectl get pv pvc` slip | ARC not installed |
| 03 | [03-arc-controller-403-then-recovered.log](03-arc-controller-403-then-recovered.log) | **ERROR** `403 Resource not accessible by integration`, then scale set registered | Self-recovered after app permission update |
| 04 | [04-arc-scale-set-install-and-runner-watch.log](04-arc-scale-set-install-and-runner-watch.log) | Scale set install (0.14.2) and an ephemeral runner running the test job | ARC works end to end |
| 05 | [05-kagent-install-controller-crashloop.log](05-kagent-install-controller-crashloop.log) | kagent 0.10.3 install, **controller CrashLoopBackOff** | Self-healed once PostgreSQL was ready |
| 06 | [06-kagent-demo-agents-and-cleanup.log](06-kagent-demo-agents-and-cleanup.log) | **10 demo agents in CreateContainerConfigError**, cleanup with overrides | Fixed with `kagent-overrides.yaml` |
| 07 | [07-bedrock-access-denied-and-model-switch.log](07-bedrock-access-denied-and-model-switch.log) | **Bedrock AccessDenied** for Sonnet 5.5, agreement flow, switch to Sonnet 4.6, IRSA | Running on Sonnet 4.6 |
| 08 | [08-readonly-tool-server-connection-refused.log](08-readonly-tool-server-connection-refused.log) | Tool list, read-only copy, **`connection refused` race** | Accepted on the next 60s reconcile |
| 09 | [09-docker-build-helm-404.log](09-docker-build-helm-404.log) | **Docker build failed: Helm download 404** (`v3.x.y` placeholder) | Fixed with `--build-arg HELM_VERSION` |
| 10 | [10-mcp-sdk-v2-module-not-found.log](10-mcp-sdk-v2-module-not-found.log) | **`ModuleNotFoundError: mcp.server.fastmcp`** (MCP SDK 2.x) | Fixed by pinning `mcp[cli]<2` |
| 11 | [11-mcp-sdk-pin-and-rollout.log](11-mcp-sdk-pin-and-rollout.log) | Rebuild 0.1.1 and rollout | Image fixed |
| 12 | [12-tool-servers-accepted-and-agent-ready.log](12-tool-servers-accepted-and-agent-ready.log) | Both tool servers accepted, agent READY with IRSA SA | Ready |
| 13 | [13-agent-first-run-tool-calls.log](13-agent-first-run-tool-calls.log) | Agent startup + first run: 9 read-only tool calls | Report produced |
| 14 | [14-agent-full-report-ui-export.log](14-agent-full-report-ui-export.log) | Full report text copied from the kagent UI (plus markdown re-render) | NO-GO, 7 findings; [cleaned report](../reports/2026-10-12-arc-0.14.2-to-0.15.0.md) |

Explanations and fixes for every error are in [../docs/troubleshooting.md](../docs/troubleshooting.md).
