# Changelog

## 0.2.0-alpha.1 - 2026-06-01

- G010: Added `CommandRunner`, provider config, and mock/Claude/Codex provider adapters. Claude uses `claude -p`; Codex uses `codex exec --sandbox workspace-write`; mock mode never calls external CLIs.
- G011: Added formal Workflow2 phase statuses, legal transition helpers, append-only event support, run summary helpers, and conservative structured verdict parsing.
- G012: Added safe Frontier-owned worktree planning and management with sanitized branch/path creation and protected cleanup behavior.
- G013: Added GitHub CLI utilities and merge gate dry-run outputs. Real PR creation and real merge require explicit env authorization and lane policy.
- G014: Replaced canary scaffolds with temp-repo negative canaries for broad staging, test tamper, secrets, large artifacts, destructive commands, boundary escapes, raw data, and scope drift.
- G015: Implemented `tools/upgrade_frontier.py` and `tools/diff_template.py` for safe generic-harness sync while preserving project-specific files by default.
- G016: Added generated config validation for schema, lanes, Workflow2 settings, artifact policy, provider config, and env overrides.
- G017: Updated versioning and docs for the v0.2 alpha runtime, supported commands, safety defaults, and upgrade workflow.

## 3.0.0 - 2026-05-31

- Expanded the template into Frontier Harness Generic v3.0.
- Added profile-based universal bootstrap coverage including `app_product`.
- Added generated project tool stubs for Frontier phase, campaign, state, review, merge, artifact, cost, GitHub, and Ralph workflows.
- Added Claude hooks, additional GitHub workflow scaffolds, Ralph script templates, and eval/canary scaffolding.
- Upgraded generated `frontier.yaml`, skills, agents, docs, and justfile to describe Workflow 1 and Workflow 2 control-plane behavior.

## 0.1.0 - 2026-05-31

- Added initial generic Frontier Harness template repository.
- Added profile definitions for generic, software, research, trading research, trading broker, data pipeline, docs writing, and infrastructure projects.
- Added render, bootstrap, diff, and upgrade CLI entry points.
- Added tests for profile validity, rendering, overwrite protection, and unresolved template variables.
