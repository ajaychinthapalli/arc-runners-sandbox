# arc-release-info

MCP tool server the agent uses for data that isn't in the cluster: ARC and runner releases on GitHub, and the CRDs inside the target ARC Helm chart.

| Tool | Source | Returns |
| --- | --- | --- |
| `arc_latest()` | GitHub releases API | Latest stable `gha-runner-scale-set` version (e.g. `0.15.0`) |
| `arc_releases(installed, target)` | GitHub releases API | Every release in `(installed, target]` with its notes |
| `runner_latest()` | GitHub releases API | Latest `actions/runner` version |
| `crd_diff(target)` | Kubernetes API + `helm pull` from ghcr.io | Per CRD: `new` / `changed` vs the live cluster |

## Build and push (amd64 nodes)

```bash
source ../../.env
aws ecr create-repository --repository-name arc-release-info --region $REGION \
  --image-scanning-configuration scanOnPush=true
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR
docker buildx build --platform linux/amd64 \
  --build-arg HELM_VERSION=$HELM_VERSION \
  -t $ECR/arc-release-info:0.1.1 --push .
```

Check node architecture first: `kubectl get nodes -L kubernetes.io/arch`.

## Notes

- Runs as UID 65534 with a read-only root filesystem; `/tmp` is an `emptyDir` and `HOME=/tmp` so `helm pull` can cache.
- Needs egress to `api.github.com` and `ghcr.io`, plus `get/list` on CRDs.
- `crd_diff` compares raw schemas, so defaulted fields can show as `changed`; treat it as "read the CRD changes", not proof of a breaking change.
- Migrating to MCP SDK 2.x (`MCPServer`) is a follow-up; until then keep `mcp[cli]<2`.
