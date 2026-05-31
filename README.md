# Frontier Harness Template

Frontier Harness Template is a generic reusable repository template for bootstrapping AI-assisted project harnesses. It generates project-local operating docs, agent and skill scaffolds, campaign folders, review and handoff records, validation docs, and lightweight automation hooks.

This repository is the template source. It is not a business project and does not include live trading, autonomous merge behavior, or project-specific integrations.

## What It Generates

- `AGENTS.md` and `CLAUDE.md` operating instructions
- `frontier.yaml` harness metadata
- Codex and Claude skill and agent scaffolds
- campaign, spec, handoff, review, decision, run, and docs directories
- git hooks, a pull request template, and a minimal CI workflow
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
- `research`
- `trading_research`
- `trading_broker`
- `data_pipeline`
- `docs_writing`
- `infra`

The trading profiles are harness profiles only. This template does not integrate with brokers, trading systems, or auto-merge workflows.

## Development

```bash
python -m compileall tools tests
python -m pytest
```

The bootstrap command refuses to overwrite existing files unless `--force` is passed and validates that rendered paths remain inside the requested target directory.
