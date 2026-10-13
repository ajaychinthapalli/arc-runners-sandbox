"""arc-release-info: MCP tool server for the ARC Upgrade Readiness Agent.

Tools
  arc_latest()                   latest stable gha-runner-scale-set version
  arc_releases(installed,target) releases in (installed, target] with release notes
  runner_latest()                latest actions/runner version
  crd_diff(target)               live actions.github.com CRDs vs the target chart's CRDs

Requires the MCP Python SDK 1.x (`mcp[cli]<2`); SDK 2.x renamed FastMCP.
"""
import os, subprocess, tempfile, pathlib, httpx, yaml
from kubernetes import client, config
from mcp.server.fastmcp import FastMCP

# host must be 0.0.0.0: FastMCP binds to localhost by default, which a Service cannot reach.
mcp = FastMCP("arc-release-info", host="0.0.0.0", port=8080)
GH = httpx.Client(base_url="https://api.github.com", timeout=30, headers={
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.getenv("GITHUB_TOKEN") else {})
CHART = "oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller"
PREFIX = "gha-runner-scale-set-"

def _ver(tag: str) -> tuple:
    return tuple(int(x) for x in tag.rsplit("-", 1)[-1].lstrip("v").split("."))

def _releases() -> list:
    return [r for r in GH.get("/repos/actions/actions-runner-controller/releases",
                              params={"per_page": 100}).json()
            if r["tag_name"].startswith(PREFIX) and not r["prerelease"]]

@mcp.tool()
def arc_latest() -> str:
    """Latest stable gha-runner-scale-set release version."""
    return max((r["tag_name"] for r in _releases()), key=_ver).removeprefix(PREFIX)

@mcp.tool()
def arc_releases(installed: str, target: str) -> list:
    """Releases after `installed` up to and including `target`, with release notes."""
    lo, hi = _ver(installed), _ver(target)
    return [{"version": r["tag_name"].removeprefix(PREFIX), "notes": r["body"]}
            for r in sorted(_releases(), key=lambda r: _ver(r["tag_name"]))
            if lo < _ver(r["tag_name"]) <= hi]

@mcp.tool()
def runner_latest() -> str:
    """Latest actions/runner release version."""
    return GH.get("/repos/actions/runner/releases/latest").json()["tag_name"].lstrip("v")

@mcp.tool()
def crd_diff(target: str) -> list:
    """Compare live actions.github.com CRDs with the CRDs in the target controller chart."""
    config.load_incluster_config()
    api = client.ApiClient()
    live = {c.metadata.name: c for c in
            client.ApiextensionsV1Api().list_custom_resource_definition().items
            if c.spec.group == "actions.github.com"}
    out = []
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["helm", "pull", CHART, "--version", target, "--untar", "-d", d],
                       check=True, capture_output=True)
        for f in sorted(pathlib.Path(d).rglob("crds/*.yaml")):
            crd = yaml.safe_load(f.read_text())
            name = crd["metadata"]["name"]
            new = {v["name"]: v.get("schema") for v in crd["spec"]["versions"]}
            old = {v["name"]: v.get("schema") for v in
                   api.sanitize_for_serialization(live[name])["spec"]["versions"]} if name in live else {}
            out.append({"crd": name, "new": name not in live, "changed": new != old})
    return out

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
