# Template Version

Version: `v0.3.0-rc1`

Frontier Harness `v0.3.0-rc1` is a production-grade release candidate for the generic Workflow2/Ralph runtime.

Release-candidate semantics:

- Real Workflow2 loops are supported: campaign, phase selection, Claude spec, Codex execution, validation, Claude review, repair, done-check, git commit/push, PR, CI wait, merge gate, lane-based auto-merge, next phase, and `RUN_SUMMARY.md`.
- Real auto-merge is supported for green/yellow lanes when `frontier.yaml` lane policy, CI, verdicts, artifact policy, branch protection validation, and authenticated `gh` all pass.
- Red lane always requires explicit authorization with `FRONTIER_RED_AUTHORIZED=1` and a matching scope.
- Worktree mode is supported but remains off by default for compatibility.
- Downstream validation is still required before unbounded overnight runs in serious repositories.

Generated projects do not include broker, live trading, paper trading, production deployment, or project-specific business logic.
