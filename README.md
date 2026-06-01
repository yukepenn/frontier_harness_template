# Frontier Harness Template

This repository is the source for Frontier Harness `v0.3.0-rc1`: a generic, repo-native Workflow2/Ralph runtime template for campaign-driven engineering work.

It renders reusable harness files only. It does not include project business logic, broker integrations, live trading, paper trading, production deployment, or direct provider API-key handling.

## What v0.3.0-rc1 Supports

- Provider-wired Workflow2 loops with Claude spec generation, Codex execution, validation, Claude review, Codex repair, semantic done-checks, and campaign done-checks.
- Official local CLI patterns: `claude -p` and `codex exec --sandbox workspace-write`.
- Mock mode that never calls provider CLIs.
- GitHub PR creation, existing PR detection, CI polling, branch protection validation, merge gate artifacts, and lane-based auto-merge through `gh`.
- Explicit curated git staging, commit, and push per phase. The runtime never uses `git add .` or `git add -A`.
- Run locks, heartbeat files, STOP files, budget stops, resumable checkpoints, and overnight mode.
- Optional Frontier-owned worktree mode.
- Post-bootstrap acceptance checks with `just frontier-acceptance`.

## Bootstrap

```bash
python tools/bootstrap_frontier.py \
  --target /tmp/frontier_sample_project \
  --profile generic \
  --project-name sample_project \
  --force
```

Existing target files are not overwritten unless `--force` is passed.

## Main Generated Commands

```bash
just frontier-run-campaign <campaign>
just frontier-run-next <campaign>
just frontier-run-campaign-mock <campaign>
just frontier-run-next-mock <campaign>
just frontier-run-campaign-ledger <campaign>
just frontier-run-overnight <campaign>
just frontier-resume <run_id>
just frontier-tail <run_id>
just frontier-summary <run_id>
just frontier-stop <run_id>
just frontier-acceptance
```

Mock one-phase:

```bash
FRONTIER_MOCK_PROVIDERS=1 FRONTIER_MAX_PHASES=1 just frontier-run-campaign G005_WORKFLOW2_TOY
```

Provider-wired one-phase:

```bash
FRONTIER_MAX_PHASES=1 just frontier-run-campaign G005_WORKFLOW2_TOY
```

Overnight:

```bash
just frontier-run-overnight G005_WORKFLOW2_TOY
```

Real green/yellow auto-merge uses `frontier.yaml` lane policy plus authenticated `gh`, required CI success, passing verdicts, artifact policy success, and branch protection validation. Red lane additionally requires `FRONTIER_RED_AUTHORIZED=1` and matching scope.

## Upgrade Existing Projects

```bash
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --dry-run
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --dry-run --plan-json upgrade-plan.json --report-md upgrade-report.md
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --apply
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --apply --force-project-files
```

The upgrade tool preserves project-specific files by default, including campaigns, `ACTIVE_CAMPAIGN.md`, `PROJECT_STATUS.md`, `PROGRESS.md`, and `frontier.yaml`.

## Development Validation

```bash
python -m compileall tools tests
python -m pytest
python tools/bootstrap_frontier.py --target /tmp/frontier_sample_project --profile generic --project-name sample_project --force
```

Rendered projects should also pass `python -m compileall tools tests`, `python -m pytest`, `just frontier-doctor`, `just verify-canaries`, a mock one-phase Workflow2 run, `python tools/verify.py --artifacts`, and `just frontier-acceptance`.
