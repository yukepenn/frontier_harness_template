# AGENTS.md

This repository is the source for Frontier Harness Generic v3.0. Work here should keep the template reusable, project-neutral, and reviewable.

## Scope

- Maintain template files, profiles, tests, docs, and bootstrap tooling.
- Do not add project-specific business logic.
- Do not add broker, live trading, or paper trading integrations.
- Keep generated Workflow 2, Ralph, and auto-merge components as scaffolding unless a later goal explicitly asks for real provider or GitHub orchestration.
- Do not clone, modify, or depend on downstream repositories.

## Engineering Rules

- Keep dependencies minimal.
- Prefer Python standard library code unless a dependency is clearly justified.
- Rendered output must stay within the requested target directory.
- Existing target files must not be overwritten unless the caller passes `--force`.
- Template files should avoid unresolved template variables after rendering.

## Validation

Run before committing template or tool changes:

```bash
python -m compileall tools tests
python -m pytest
python tools/bootstrap_frontier.py --target /tmp/frontier_sample_project --profile generic --project-name sample_project --force
```

Then verify the sample project contains `AGENTS.md`, `CLAUDE.md`, `frontier.yaml`, `campaigns`, `specs`, `handoffs`, and `reviews`.
