import importlib.util
import json
import re
import subprocess
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
    "tests/test_ralph_driver.py",
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
    "campaigns/G005_WORKFLOW2_TOY/GOAL.md",
    "campaigns/G005_WORKFLOW2_TOY/PHASE_PLAN.md",
    "campaigns/G005_WORKFLOW2_TOY/campaign.yaml",
    "campaigns/G005_WORKFLOW2_TOY/ACCEPTANCE.md",
    "campaigns/G005_WORKFLOW2_TOY/RISK_REGISTER.md",
    "campaigns/G005_WORKFLOW2_TOY/RUNBOOK.md",
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

TOY_PHASE_IDS = [
    "P01_CREATE_TOY_DOC_A",
    "P02_CREATE_TOY_DOC_B",
    "P03_CREATE_TOY_SUMMARY",
]


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


def test_rendered_claude_settings_use_supported_hook_events(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    settings_text = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    settings = json.loads(settings_text)
    hooks = settings.get("hooks", {})
    old_hook_keys = {"pre_tool_use", "post_tool_use", "notification", "stop"}
    expected_commands = {
        "PreToolUse": ".claude/hooks/pre-tool-use.sh",
        "PostToolUse": ".claude/hooks/post-tool-use.sh",
        "Notification": ".claude/hooks/notification.sh",
        "Stop": ".claude/hooks/stop-hook.sh",
    }
    assert set(expected_commands) <= set(hooks)
    assert not old_hook_keys & set(hooks)
    for old_hook_key in old_hook_keys:
        assert f'"{old_hook_key}"' not in settings_text
    for event_name, expected_command in expected_commands.items():
        matcher_groups = hooks[event_name]
        assert isinstance(matcher_groups, list), event_name
        assert matcher_groups, event_name
        for matcher_group in matcher_groups:
            assert isinstance(matcher_group, dict), event_name
            handlers = matcher_group.get("hooks")
            assert isinstance(handlers, list), event_name
            assert handlers, event_name
        commands = [
            handler.get("command")
            for matcher_group in matcher_groups
            for handler in matcher_group["hooks"]
            if isinstance(handler, dict) and handler.get("type") == "command"
        ]
        assert expected_command in commands


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


def test_rendered_workflow2_toy_campaign_runs_locally(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    result = run_command(
        [
            "python",
            "tools/frontier/ralph_driver.py",
            "run",
            "--campaign-id",
            "G005_WORKFLOW2_TOY",
        ],
        tmp_path,
    )

    assert "Completed Workflow 2 toy run" in result.stdout
    assert (tmp_path / "docs" / "toy_workflow2" / "phase_a.md").is_file()
    assert (tmp_path / "docs" / "toy_workflow2" / "phase_b.md").is_file()
    assert (tmp_path / "docs" / "toy_workflow2" / "summary.md").is_file()

    run_dirs = sorted(
        (tmp_path / "runs").glob("*G005_WORKFLOW2_TOY*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    assert run_dirs
    latest_run = run_dirs[0]
    assert (latest_run / "state.json").is_file()
    assert (latest_run / "events.jsonl").is_file()
    assert (latest_run / "RUN_SUMMARY.md").is_file()

    state = json.loads((latest_run / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "COMPLETED"
    assert state["campaign_id"] == "G005_WORKFLOW2_TOY"
    assert state["external_providers_called"] is False
    assert state["network_used"] is False
    assert state["auto_merge_performed"] is False

    for phase_id in TOY_PHASE_IDS:
        phase_dir = latest_run / "phases" / phase_id
        assert (phase_dir / "spec.md").is_file()
        assert (phase_dir / "handoff.md").is_file()
        assert (phase_dir / "review.md").is_file()
        verdict_path = phase_dir / "verdict.json"
        assert verdict_path.is_file()
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        assert verdict["verdict"] == "PASS"
        assert verdict["external_providers_called"] is False
        assert verdict["network_used"] is False
        assert verdict["auto_merge_performed"] is False


def test_rendered_provider_wired_runtime_and_ci_are_present(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    driver = (tmp_path / "tools" / "frontier" / "ralph_driver.py").read_text(encoding="utf-8")
    justfile = (tmp_path / "justfile").read_text(encoding="utf-8")
    workflow = (tmp_path / ".github" / "workflows" / "frontier-ci.yml").read_text(encoding="utf-8")

    assert (tmp_path / "tests" / "test_ralph_driver.py").is_file()
    assert "ralph_frontier_provider_wired_mvc_v1" in driver
    assert "def run_provider_wired_campaign" in driver
    assert "def run_ledger_only_campaign" in driver
    assert "ALPHA_SYSTEM_V1" not in driver
    assert "alpha_system" not in driver

    run_campaign = recipe_body(justfile, "frontier-run-campaign")
    run_next = recipe_body(justfile, "frontier-run-next")
    ledger = recipe_body(justfile, "frontier-run-campaign-ledger")
    assert "--provider-wired" in run_campaign
    assert "FRONTIER_MAX_PHASES=1" not in run_campaign
    assert "--provider-wired" in run_next
    assert "FRONTIER_MAX_PHASES=1" in run_next
    assert "--ledger-only" in ledger

    assert "python -m pip install pytest pyyaml jinja2" in workflow
    assert "find tests -type f" in workflow
    assert "python -m pytest" in workflow
    assert "No tests configured yet" in workflow


def test_rendered_project_compileall_and_pytest_pass(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    run_command(["python", "-m", "compileall", "tools", "tests"], tmp_path)
    run_command(["python", "-m", "pytest"], tmp_path)


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Command failed: {' '.join(command)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


def recipe_body(justfile_text: str, recipe_name: str) -> str:
    pattern = re.compile(rf"^{re.escape(recipe_name)}(?:\s[^:]*)?:\n((?:    .+\n)+)", re.MULTILINE)
    match = pattern.search(justfile_text)
    assert match is not None, recipe_name
    return match.group(1)


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
        [
            "AGENTS.md",
            "frontier.yaml",
            ".codex/agents/worker.toml",
            "tools/hooks/forbidden_pattern_guard.py",
        ]
    ) == 0

    policy_file = tmp_path / "docs" / "negative-policy.yaml"
    policy_file.write_text("instruction: do not use git add" + " .\n", encoding="utf-8")
    assert forbidden_pattern_guard.main(["docs/negative-policy.yaml"]) == 0

    unsafe_script = tmp_path / "scripts" / "unsafe.sh"
    unsafe_script.write_text("git push" + " --force\n", encoding="utf-8")
    assert forbidden_pattern_guard.main(["scripts/unsafe.sh"]) == 1


def test_rendered_scaffold_can_commit_with_policy_metadata(
    tmp_path: Path,
) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    written = render_tree(repo_root() / "templates", tmp_path, context)
    relative_paths = sorted(str(path.relative_to(tmp_path)) for path in written)
    assert ".codex/agents/worker.toml" in relative_paths

    run_command(["git", "init"], tmp_path)
    run_command(["git", "config", "user.name", "Frontier Test"], tmp_path)
    run_command(["git", "config", "user.email", "frontier-test@example.invalid"], tmp_path)
    run_command(["git", "config", "core.hooksPath", ".githooks"], tmp_path)
    run_command(["git", "add", *relative_paths], tmp_path)
    run_command(["git", "commit", "-m", "test: bootstrap scaffold"], tmp_path)
