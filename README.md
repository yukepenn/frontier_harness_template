# Frontier Harness Generic v3.0

Frontier Harness Generic v3.0 is a WSL2-primary, repo-native, Ralph-driven, Codex-executed, Claude-reviewed, Git-memory autonomous engineering harness template.

Every serious project gets the same bootstrap harness: `AGENTS.md` constitution, `CLAUDE.md` import layer, `frontier.yaml` automation control plane, campaign contracts, phase specs, Codex execution, Claude review, Ralph strict loop scaffolding, run ledgers, CI/automerge scaffolding, and reusable project profiles.

This repository is the template source. It is not a business project and does not include broker integrations, live trading, paper trading, provider API orchestration, or a production auto-merge implementation.

## What It Generates

- `AGENTS.md` and `CLAUDE.md` operating instructions
- `frontier.yaml` harness metadata and automation lanes
- Codex and Claude skill and agent scaffolds
- Claude hook scaffolds
- campaign, spec, handoff, review, decision, run, and docs directories
- eval/canary directories
- git hooks, pull request template, and CI/automerge/nightly audit workflow scaffolds
- status and progress tracking docs

## Quick Start

```bash
python tools/bootstrap_frontier.py \
  --target /tmp/frontier_sample_project \
  --profile generic \
  --project-name sample_project \
  --force
```

Profiles live in `profiles/`. Template files live in `templates/`. Files ending in `.j2` are rendered with a small standard-library renderer; other files are copied as-is.

## Profiles

- `generic`
- `software`
- `app_product`
- `research`
- `trading_research`
- `trading_broker`
- `data_pipeline`
- `docs_writing`
- `infra`

The trading profiles are harness profiles only. This template does not integrate with brokers, trading systems, or live execution.

## Development

```bash
python -m compileall tools tests
python -m pytest
```

The bootstrap command refuses to overwrite existing files unless `--force` is passed and validates that rendered paths remain inside the requested target directory.
