# arc-runners-sandbox

Sandbox for GitHub **Actions Runner Controller (ARC)** on Amazon EKS, plus a **read-only kagent agent** that tells you whether an ARC upgrade is safe before you run it.

![ARC Upgrade Readiness Agent on Amazon EKS](images/architecture-final.jpeg)

## What's running

| Component | Version | Where |
| --- | --- | --- |
| EKS cluster `ac-ws-dev-use2` | v1.36.4, 5 × amd64 | us-east-2 |
| ARC controller + scale set `arc-runner-set` | 0.14.2 (latest is 0.15.0, on purpose) | `arc-systems`, `arc-runners` |
| kagent | 0.10.3 | `kagent` |
| Agent `arc-upgrade-readiness` | Go ADK runtime | `kagent` |
| Model | `us.anthropic.claude-sonnet-4-6` on Bedrock via IRSA | us-east-2 |
| Tool server `arc-k8s-readonly` | kagent tools 0.3.0, read-only RBAC, 5 tools exposed | `kagent` |
| Tool server `arc-release-info` | Python MCP SDK 1.x, image `0.1.1` | `kagent` |
| Test workflow | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) → `runs-on: arc-runner-set` | this repo |

## How a readiness check works

1. You ask (kagent UI, Slack, or the weekly CronJob): *"Assess upgrading ARC to the latest release."*
2. The agent reads live ARC state through `arc-k8s-readonly`: controller Deployment, AutoscalingRunnerSets, EphemeralRunners.
3. It pulls release data through `arc-release-info`: latest ARC version, release notes in between, CRD diff against the target chart, latest runner version.
4. Bedrock correlates it into **Go / No-go** + Blockers / Fix before upgrade / Warnings + an upgrade-day sequence.

Nothing in the path can write to the cluster.

**First result:** [0.14.2 → 0.15.0: NO-GO](reports/2026-10-12-arc-0.14.2-to-0.15.0.md). All 4 CRDs change, so they must be applied before `helm upgrade`; 0 jobs running, so timing is good. The analysis held up; three generated commands did not, see the [review](docs/first-run-review.md). Sequence diagram and setup flow: [docs/flows.md](docs/flows.md).

## Repo layout

```
.
├── .github/workflows/ci.yml         ARC test job (workflow_dispatch)
├── docs/
│   ├── setup-guide.md               Step 0–10 exactly as run
│   ├── troubleshooting.md           Every error hit, root cause, fix
│   ├── flows.md                     Mermaid: architecture, run sequence, setup path, error timeline
│   ├── first-run-review.md          First report checked against the cluster
│   └── design-decisions.md          Why an agent here (and not for key rotation), model/version choices
├── images/                          Architecture diagram + kagent UI screenshot
├── logs/                            14 raw captures, numbered in order (account IDs redacted)
├── reports/                         Agent reports, verbatim, with corrected commands
├── manifests/
│   ├── arc/install-arc.sh           Controller, GitHub App secret, scale set
│   └── kagent/                      Overrides, ModelConfig, tool servers, Agent, weekly CronJob
├── iam/bedrock-invoke.json.tmpl     Least-privilege Bedrock policy (envsubst)
├── tools/arc-release-info/          MCP server code + Dockerfile
└── env.example                      Variables used everywhere
```

## Quick start

```bash
cp env.example .env && source .env
# then follow docs/setup-guide.md
```

## Errors we hit (short version)

| Error | Fix |
| --- | --- |
| ARC `403 Resource not accessible by integration` | Personal-account app needs repo **Administration: RW**; self-recovered after accepting |
| kagent controller CrashLoopBackOff | Waits for bundled Postgres; self-heals |
| 10 demo agents `CreateContainerConfigError` | [`kagent-overrides.yaml`](manifests/kagent/kagent-overrides.yaml) |
| Bedrock `AccessDenied` for Sonnet 5.5 | Agreement accepted but still gated → Sonnet 4.6 |
| Tool server `connection refused` | Startup race; next reconcile OK |
| Docker build Helm 404 | Pass `--build-arg HELM_VERSION` |
| `ModuleNotFoundError: mcp.server.fastmcp` | Pin `mcp[cli]<2` |
| Report said `:latest` is outdated | Prompt rules added |
| Report used non-existent chart paths and a list `--set` | Prompt rules + corrected commands in the report |

Full detail: [docs/troubleshooting.md](docs/troubleshooting.md).

## Status

- [x] ARC installed and running jobs
- [x] kagent + Bedrock (IRSA) + both tool servers
- [x] Agent produces a report ([0.14.2 → 0.15.0](reports/2026-10-12-arc-0.14.2-to-0.15.0.md)); prompt tuned after review
- [ ] Re-run with tuned prompt
- [ ] Run the corrected 0.15.0 upgrade in this sandbox
- [ ] Step 10: weekly CronJob to Slack
- [ ] Migrate `arc-release-info` to MCP SDK 2.x
- [ ] Switch to Sonnet 5.5 once the account can invoke it
