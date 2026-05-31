import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

from tools.render_templates import build_context, load_profile, render_tree, repo_root

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


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

CODEX_AGENT_SUPPORTED_FIELDS = {
    "name",
    "description",
    "model",
    "model_reasoning_effort",
    "developer_instructions",
}


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        pytest.fail(f"{path} is missing YAML frontmatter delimited by ---")
    try:
        end = lines.index("---", 1)
    except ValueError:
        pytest.fail(f"{path} is missing closing YAML frontmatter delimiter")

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator:
            pytest.fail(f"{path} has invalid frontmatter line: {line!r}")
        metadata[key.strip()] = value.strip()
    return metadata


def parse_flat_toml(text: str, path: Path) -> dict[str, str]:
    if tomllib is not None:
        return tomllib.loads(text)

    values: dict[str, str] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            pytest.fail(f"{path} has invalid TOML line: {line!r}")
        key = key.strip()
        value = value.strip()
        if value.startswith('"""'):
            parts = [value[3:]]
            while not parts[-1].endswith('"""'):
                if index >= len(lines):
                    pytest.fail(f"{path} has unterminated multiline string for {key}")
                parts.append(lines[index])
                index += 1
            parts[-1] = parts[-1][:-3]
            values[key] = "\n".join(parts)
        elif value.startswith('"') and value.endswith('"'):
            values[key] = value[1:-1]
        else:
            values[key] = value
    return values


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


def test_rendered_codex_skills_have_frontmatter(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    skill_paths = sorted((tmp_path / ".codex" / "skills").glob("*/SKILL.md"))
    assert skill_paths
    for path in skill_paths:
        metadata = parse_frontmatter(path)
        assert metadata.get("name") == path.parent.name
        assert metadata.get("description")


def test_rendered_codex_agents_have_supported_metadata(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    agent_paths = sorted((tmp_path / ".codex" / "agents").glob("*.toml"))
    assert agent_paths
    for path in agent_paths:
        text = path.read_text(encoding="utf-8")
        metadata = parse_flat_toml(text, path)

        assert "effort =" not in text
        assert not re.search(r"(?m)^effort\s*=", text)
        assert set(metadata) <= CODEX_AGENT_SUPPORTED_FIELDS
        assert metadata.get("name") == path.stem
        assert metadata.get("description", "").strip()
        assert metadata.get("developer_instructions", "").strip()
        assert metadata.get("model_reasoning_effort") in {"high", "medium"}


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


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rendered_secret_guards_allow_harness_security_paths(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    secret_scan = load_module(tmp_path / "tools" / "hooks" / "secret_scan.py")
    artifact_policy = load_module(tmp_path / "tools" / "frontier" / "artifact_policy.py")

    allowed_paths = [
        "tools/hooks/secret_scan.py",
        "templates/tools/hooks/secret_scan.py.j2",
        "docs/artifact_policy.md",
        ".claude/rules/security.md",
        "evals/canaries/forbidden_secret/README.md",
    ]
    for relative_path in allowed_paths:
        assert not secret_scan.is_forbidden(relative_path), relative_path
        assert artifact_policy.check_path(Path(relative_path)), relative_path


def test_rendered_secret_guards_block_sensitive_artifacts(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    secret_scan = load_module(tmp_path / "tools" / "hooks" / "secret_scan.py")
    artifact_policy = load_module(tmp_path / "tools" / "frontier" / "artifact_policy.py")

    forbidden_paths = [
        ".env",
        ".env.local",
        "config/.env.production",
        "deploy.pem",
        "id_rsa.key",
        "credentials",
        "credentials/aws.json",
        "config/credential",
        "config/db_credentials.json",
        "api_token.txt",
        "github-token.yml",
        "private_key.txt",
        "my-private-key.txt",
        "secret.txt",
        "app_secret.yml",
    ]
    for relative_path in forbidden_paths:
        assert secret_scan.is_forbidden(relative_path), relative_path
        assert not artifact_policy.check_path(Path(relative_path)), relative_path


def test_rendered_frontier_policy_avoids_broad_secret_substring_globs(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    policy = (tmp_path / "frontier.yaml").read_text(encoding="utf-8")
    assert '"**/*secret*"' not in policy
    assert '"**/*credential*"' not in policy


def test_rendered_test_tamper_guard_allows_own_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    test_tamper_guard = load_module(tmp_path / "tools" / "hooks" / "test_tamper_guard.py")

    monkeypatch.chdir(tmp_path)
    assert test_tamper_guard.main(["tools/hooks/test_tamper_guard.py"]) == 0


def test_rendered_forbidden_pattern_guard_allows_policy_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    forbidden_pattern_guard = load_module(
        tmp_path / "tools" / "hooks" / "forbidden_pattern_guard.py"
    )

    monkeypatch.chdir(tmp_path)
    assert forbidden_pattern_guard.main(
        ["frontier.yaml", "tools/hooks/forbidden_pattern_guard.py"]
    ) == 0

    unsafe_script = tmp_path / "unsafe.sh"
    unsafe_script.write_text("git push --force\n", encoding="utf-8")
    assert forbidden_pattern_guard.main(["unsafe.sh"]) == 1
