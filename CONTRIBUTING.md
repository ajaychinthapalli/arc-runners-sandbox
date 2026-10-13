# Contributing

Thanks for helping improve this ARC/EKS sandbox and readiness agent setup.

## Project scope

This repository captures a sandbox environment for GitHub Actions Runner Controller (ARC), kagent, and related operational tooling. Changes should stay focused on:

- documentation and runbook clarity
- manifest and automation updates for the sandbox environment
- tool/server improvements for ARC readiness checks
- CI/test workflow fixes

Avoid unrelated application code or broad refactors that do not support the sandbox workflow.

## Local setup

1. Copy the environment template:
   ```bash
   cp env.example .env
   source .env
   ```
2. Review the setup docs in `docs/setup-guide.md` before changing manifests or workflows.
3. Keep secret values in local environment files and never commit credentials.

## Contribution expectations

- Keep changes small and targeted.
- Update documentation when behavior or setup steps change.
- Prefer clear, reproducible changes that can be reviewed from the repo alone.
- Do not commit live cluster credentials, tokens, or generated secret material.

## Pull requests

- Open a PR with a short description of the problem and fix.
- Include any relevant links to logs, reports, or troubleshooting notes.
- Call out any environment assumptions or manual follow-up steps.

## Review and validation

- Check the GitHub Actions workflow in `.github/workflows/ci.yml` if your change affects automation or tools.
- Validate any doc or manifest change against the current repo structure before merging.
- If a change affects the cluster setup, note the exact commands run and the expected impact.

## Safety notes

This repo includes operational manifests and sandbox automation. Treat all cluster and AWS settings as sensitive and avoid destructive changes outside the test environment.
