from pathlib import Path

import pytest

from tools.render_templates import build_context, load_profile, render_tree, repo_root


EXPECTED_RENDERED_PATHS = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "frontier.yaml",
    "ACTIVE_CAMPAIGN.md",
    ".codex/config.toml",
    ".codex/skills/frontier-execute/SKILL.md",
    ".codex/skills/frontier-repair/SKILL.md",
    ".codex/skills/frontier-verify/SKILL.md",
    ".codex/skills/frontier-handoff/SKILL.md",
    ".codex/agents/worker.toml",
    ".codex/agents/explorer.toml",
    ".codex/agents/fixer.toml",
    ".claude/settings.json",
    ".claude/hooks/pre-tool-use.sh",
    ".claude/hooks/post-tool-use.sh",
    ".claude/hooks/stop-hook.sh",
    ".claude/hooks/notification.sh",
    ".claude/skills/frontier-campaign/SKILL.md",
    ".claude/skills/frontier-spec/SKILL.md",
    ".claude/skills/frontier-review/SKILL.md",
    ".claude/skills/frontier-audit/SKILL.md",
    ".claude/skills/frontier-ralph/SKILL.md",
    ".claude/skills/project-skill/SKILL.md",
    ".claude/skills/project-skill/lessons.md",
    ".claude/skills/project-skill/glossary.md",
    ".claude/agents/researcher.md",
    ".claude/agents/architect.md",
    ".claude/agents/reviewer.md",
    ".claude/agents/verifier.md",
    ".claude/agents/done_checker.md",
    ".claude/agents/release_manager.md",
    ".claude/agents/harness_maintainer.md",
    ".claude/rules/python.md",
    ".claude/rules/tests.md",
    ".claude/rules/artifacts.md",
    ".claude/rules/security.md",
    ".claude/rules/project_boundaries.md",
    ".githooks/pre-commit",
    ".githooks/pre-push",
    ".github/pull_request_template.md",
    ".github/workflows/frontier-ci.yml",
    ".github/workflows/frontier-canaries.yml",
    ".github/workflows/frontier-automerge.yml",
    ".github/workflows/frontier-nightly-audit.yml",
    "tools/verify.py",
    "tools/frontier/bootstrap.py",
    "tools/frontier/phase.py",
    "tools/frontier/campaign.py",
    "tools/frontier/ralph_driver.py",
    "tools/frontier/state_machine.py",
    "tools/frontier/worktree_manager.py",
    "tools/frontier/verdict.py",
    "tools/frontier/merge_gate.py",
    "tools/frontier/op_gate.py",
    "tools/frontier/git_utils.py",
    "tools/frontier/github_utils.py",
    "tools/frontier/cost_ledger.py",
    "tools/frontier/artifact_policy.py",
    "tools/frontier/spec_schema.py",
    "tools/frontier/review_schema.py",
    "tools/frontier/campaign_schema.py",
    "tools/frontier/report.py",
    "tools/hooks/pre_commit.py",
    "tools/hooks/pre_push.py",
    "tools/hooks/secret_scan.py",
    "tools/hooks/bulk_add_guard.py",
    "tools/hooks/test_tamper_guard.py",
    "tools/hooks/forbidden_pattern_guard.py",
    "tools/hooks/artifact_guard.py",
    "tools/hooks/boundary_guard.py",
    "tools/hooks/canary_runner.py",
    "scripts/ralph/ralph.sh",
    "scripts/ralph/prompt.md",
    "scripts/ralph/CLAUDE.md",
    "scripts/ralph/frontier_adapter.md",
    "scripts/ralph/README.md",
    "campaigns/README.md",
    "campaigns/000-template/GOAL.md",
    "campaigns/000-template/PHASE_PLAN.md",
    "campaigns/000-template/campaign.yaml",
    "campaigns/000-template/ACCEPTANCE.md",
    "campaigns/000-template/RISK_REGISTER.md",
    "campaigns/000-template/RUNBOOK.md",
    "specs/README.md",
    "specs/000-template.md",
    "handoffs/README.md",
    "handoffs/000-template.md",
    "reviews/README.md",
    "reviews/000-template.md",
    "decisions/README.md",
    "decisions/ADR-000-template.md",
    "runs/README.md",
    "runs/.gitkeep",
    "evals/canaries/README.md",
    "evals/canaries/forbidden_git_add_dot/README.md",
    "evals/canaries/forbidden_test_tamper/README.md",
    "evals/canaries/forbidden_secret/README.md",
    "evals/canaries/forbidden_large_binary/README.md",
    "evals/canaries/forbidden_destructive_op/README.md",
    "evals/canaries/forbidden_boundary_import/README.md",
    "evals/canaries/forbidden_raw_data_commit/README.md",
    "evals/canaries/forbidden_scope_drift/README.md",
    "evals/behaviors/README.md",
    "evals/behaviors/heldout_behavior_001.md",
    "evals/behaviors/heldout_behavior_002.md",
    "docs/architecture.md",
    "docs/workflow.md",
    "docs/validation.md",
    "docs/operations.md",
    "docs/model_routing.md",
    "docs/artifact_policy.md",
    "docs/campaign_authoring.md",
    "docs/automation_lanes.md",
]


def test_render_tree_writes_expected_files(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    written = render_tree(repo_root() / "templates", tmp_path, context)

    assert written
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / "frontier.yaml").is_file()
    assert (tmp_path / "campaigns").is_dir()
    assert (tmp_path / "specs").is_dir()
    assert (tmp_path / "handoffs").is_dir()
    assert (tmp_path / "reviews").is_dir()
    for relative_path in EXPECTED_RENDERED_PATHS:
        assert (tmp_path / relative_path).exists(), relative_path
    assert not any(path.name.endswith(".j2") for path in tmp_path.rglob("*"))


def test_render_tree_refuses_overwrite_without_force(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    with pytest.raises(FileExistsError):
        render_tree(repo_root() / "templates", tmp_path, context)


def test_render_tree_allows_force_overwrite(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)
    render_tree(repo_root() / "templates", tmp_path, context, force=True)

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8").startswith("# sample_project")


def test_rendered_shell_hooks_are_executable(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    executable_paths = [
        tmp_path / ".githooks" / "pre-commit",
        tmp_path / ".githooks" / "pre-push",
        tmp_path / ".claude" / "hooks" / "pre-tool-use.sh",
        tmp_path / "scripts" / "ralph" / "ralph.sh",
    ]
    for path in executable_paths:
        assert path.stat().st_mode & 0o111, path
