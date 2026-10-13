# Design decisions

| Decision | Why | Alternative considered |
| --- | --- | --- |
| **Agent is strictly read-only** | Worst case of a bad answer or prompt injection is a misleading report, never a cluster change. Upgrade itself stays human-run | Letting the agent open fix PRs (possible later, via a separate bot identity) |
| **Separate read-only copy of kagent's tool server** | Bundled `kagent-tools` has broad RBAC for other agents. Two layers: RBAC blocks writes, `toolNames` hides write tools (5 of 126 exposed) | Reusing `kagent-tool-server` with only `toolNames` filtering |
| **Custom `arc-release-info` MCP server** | GitHub release notes and target-chart CRDs aren't in the cluster | Letting the model browse the web (less reliable, wider egress) |
| **kagent 0.10.3** (not 0.9.x, not 1.0 alpha) | Latest stable at the time; still `kagent.dev/v1alpha2`; only breaking change (querydoc removal) doesn't matter here | 1.0 alpha changes CRDs |
| **Bedrock with IRSA, `us.` inference profile** | No static keys; data stays in US regions; Bedrock Claude models only support inference-profile invocation | `global.` profile (more capacity, can leave the US) |
| **Claude Sonnet 4.6** instead of Sonnet 5.5 | Sonnet 5.5 not invokable on the account yet (see troubleshooting #6). Sonnet-class is enough for correlation; ~18k tokens/run | Opus (unnecessary cost), Haiku (weaker on long release notes) |
| **ARC 0.14.2 installed on purpose** | One release behind latest (0.15.0) so the agent has a real upgrade to assess | Latest ARC (nothing to assess) |
| **Personal account, repo-level runners** | Sandbox repo `arc-runners-sandbox`, private (self-hosted runners on public repos run fork PR code) | Org-level runners (needs an org) |
| **Bundled PostgreSQL** | Dev cluster only; chart warns it's not for production | External Postgres (`database.postgres.url`) for prod |
