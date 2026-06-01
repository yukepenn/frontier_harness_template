# Frontier Harness Template

This repository is the source for Frontier Harness `0.2.0-alpha.1`: a generic, repo-native runtime template for campaign-driven engineering work.

It renders reusable harness files only. It does not include project business logic, broker integrations, live trading, paper trading, production deployment, real auto-merge defaults, or secret handling beyond local guards and scans.

## What v0.2 Supports

- Generic bootstrap profiles for new repositories.
- Provider-wired local Workflow2 campaign runs with mock, Claude, and Codex adapters.
- Claude headless calls through `claude -p`.
- Codex non-interactive editable calls through `codex exec --sandbox workspace-write`.
- Formal Workflow2 phase statuses and structured verdict parsing.
- Safe worktree branch/path planning, with no worktree mode as the safer default.
- GitHub PR/CI/merge gate dry-runs through `gh`-style helpers.
- Real negative canaries and hook guards for secrets, artifacts, broad staging, test tamper, destructive commands, boundary escapes, raw data, and scope drift.
- Safe upgrade/diff tooling for syncing generic harness files into existing projects.

## What Remains Dry-Run Or Opt-In

- PR creation is dry-run unless `FRONTIER_CREATE_PR=1`.
- Auto-merge is dry-run unless `FRONTIER_ALLOW_AUTOMERGE=1` and lane policy explicitly allows it.
- Red-lane merge paths require `FRONTIER_RED_AUTHORIZED=1` plus project-scoped authorization.
- Worktree mode is implemented, but generated projects default to no-worktree unless config, env, or CLI enables it.

## Bootstrap

```bash
python tools/bootstrap_frontier.py \
  --target /tmp/frontier_sample_project \
  --profile generic \
  --project-name sample_project \
  --force
```

Existing target files are not overwritten unless `--force` is passed.

## Upgrade Existing Projects

```bash
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --dry-run
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --apply
python tools/upgrade_frontier.py --target <repo> --profile <profile> --project-name <name> --apply --force-project-files
```

The upgrade tool renders to a temp directory, classifies files, updates generic harness files on `--apply`, and preserves project-specific files by default.

## Development Validation

```bash
python -m compileall tools tests
python -m pytest
python tools/bootstrap_frontier.py --target /tmp/frontier_sample_project --profile generic --project-name sample_project --force
```

Generated projects should also pass `python -m compileall tools tests`, `python -m pytest`, `just frontier-doctor`, `just verify-canaries`, a mock one-phase Workflow2 run, and artifact verification.
