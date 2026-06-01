# Template Version

Version: `0.2.0-alpha.1`

Frontier Harness runtime hardening release.

Compatibility notes:

- Keeps the v0.1.7 provider-wired local Workflow2 MVP behavior working.
- Adds generic provider adapters, command runner, formal phase state machine, verdict schema, worktree planning, dry-run GitHub PR/CI/merge gate helpers, real negative canaries, config validation, and upgrade tooling.
- Real PR creation and real automerge remain opt-in and require explicit environment and lane-policy authorization.
- Generated projects do not include broker, live trading, paper trading, production deployment, or destructive cleanup integrations.
