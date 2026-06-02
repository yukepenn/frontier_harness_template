from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import e2e_workflow2_github as e2e


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path | None, str | None]] = []

    def run(self, command, *, cwd=None, env=None, input_text=None, timeout=600):
        del env, timeout
        command = [str(part) for part in command]
        self.calls.append((command, cwd, input_text))
        return e2e.CommandResult(command, 0, "ok\n", "")


def make_config(
    *,
    repo_prefix: str = "frontier-harness-e2e",
    repo_name: str = "frontier-harness-e2e-123",
    visibility: str = "public",
    require_branch_protection: bool = True,
    delete_repo: bool = False,
    archive_repo: bool = False,
) -> e2e.E2EConfig:
    return e2e.E2EConfig(
        owner="owner",
        repo_prefix=repo_prefix,
        repo_name=repo_name,
        visibility=visibility,
        require_branch_protection=require_branch_protection,
        delete_repo=delete_repo,
        archive_repo=archive_repo,
    )


def command_with_prefix(runner: RecordingRunner, prefix: list[str]) -> list[str]:
    for command, _cwd, _input_text in runner.calls:
        if command[: len(prefix)] == prefix:
            return command
    raise AssertionError(f"missing command with prefix: {prefix}")


def test_real_github_e2e_requires_env_gate() -> None:
    with pytest.raises(RuntimeError, match="FRONTIER_REAL_GITHUB_E2E=1"):
        e2e.load_config({})


def test_repo_creation_uses_public_by_default_when_branch_protection_required() -> None:
    runner = RecordingRunner()
    config = e2e.load_config({"FRONTIER_REAL_GITHUB_E2E": "1", "FRONTIER_E2E_OWNER": "owner"})

    e2e.create_repo(config, runner)  # type: ignore[arg-type]

    command = command_with_prefix(runner, ["gh", "repo", "create"])
    assert config.visibility == "public"
    assert config.require_branch_protection is True
    assert "--public" in command
    assert "--private" not in command


def test_repo_creation_uses_private_when_requested() -> None:
    runner = RecordingRunner()
    config = e2e.load_config(
        {
            "FRONTIER_REAL_GITHUB_E2E": "1",
            "FRONTIER_E2E_OWNER": "owner",
            "FRONTIER_E2E_VISIBILITY": "private",
        }
    )

    e2e.create_repo(config, runner)  # type: ignore[arg-type]

    command = command_with_prefix(runner, ["gh", "repo", "create"])
    assert config.visibility == "private"
    assert "--private" in command
    assert "--public" not in command


def test_disposable_repo_guard_rejects_non_prefix() -> None:
    config = make_config()

    with pytest.raises(RuntimeError, match="non-disposable"):
        e2e.assert_disposable(config, "production-repo")


def test_branch_protection_payload_keeps_validate_and_admin_enforcement() -> None:
    runner = RecordingRunner()
    config = make_config()

    e2e.configure_branch_protection(config, runner)  # type: ignore[arg-type]

    assert len(runner.calls) == 1
    command, _cwd, input_text = runner.calls[0]
    assert command[:4] == ["gh", "api", "--method", "PUT"]
    assert "--" + "admin" not in command
    assert input_text is not None
    payload = json.loads(input_text)
    assert payload["required_status_checks"]["contexts"] == ["validate"]
    assert payload["enforce_admins"] is True
    assert payload["allow_force_pushes"] is False
    assert payload["allow_deletions"] is False


def test_private_branch_protection_plan_403_gets_clear_instruction() -> None:
    class BranchProtection403Runner(RecordingRunner):
        def run(self, command, *, cwd=None, env=None, input_text=None, timeout=600):
            del cwd, env, input_text, timeout
            command = [str(part) for part in command]
            self.calls.append((command, None, None))
            return e2e.CommandResult(
                command,
                1,
                "",
                "HTTP 403: Upgrade to GitHub Pro or make this repository public to enable this feature.",
            )

    runner = BranchProtection403Runner()
    config = make_config(visibility="private")

    with pytest.raises(RuntimeError, match="FRONTIER_E2E_VISIBILITY=public"):
        e2e.configure_branch_protection(config, runner)  # type: ignore[arg-type]


def test_merge_repo_settings_use_repo_edit_flags_when_available() -> None:
    class RepoEditHelpRunner(RecordingRunner):
        def run(self, command, *, cwd=None, env=None, input_text=None, timeout=600):
            del env, timeout
            command = [str(part) for part in command]
            self.calls.append((command, cwd, input_text))
            if command == ["gh", "repo", "edit", "--help"]:
                return e2e.CommandResult(
                    command,
                    0,
                    "\n".join(
                        [
                            "--enable-squash-merge",
                            "--enable-auto-merge",
                            "--delete-branch-on-merge",
                        ]
                    ),
                    "",
                )
            return e2e.CommandResult(command, 0, "ok\n", "")

    runner = RepoEditHelpRunner()
    config = make_config()

    e2e.configure_merge_repo_settings(config, runner)  # type: ignore[arg-type]

    commands = [command for command, _cwd, _input_text in runner.calls]
    assert ["gh", "repo", "edit", config.full_name, "--enable-squash-merge"] in commands
    assert ["gh", "repo", "edit", config.full_name, "--enable-auto-merge"] in commands
    assert ["gh", "repo", "edit", config.full_name, "--delete-branch-on-merge"] in commands


def test_delete_repo_cleanup_runs_on_branch_protection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def fake_create_repo(config: e2e.E2EConfig, runner: e2e.Runner) -> None:
        del config, runner
        events.append("create")

    def fake_configure_merge_repo_settings(config: e2e.E2EConfig, runner: e2e.Runner) -> None:
        del config, runner
        events.append("merge-settings")

    def fake_bootstrap_project(
        config: e2e.E2EConfig, temp_root: Path, runner: e2e.Runner
    ) -> tuple[Path, str, str]:
        del runner
        events.append("bootstrap")
        return temp_root / config.repo_name, "campaign", "before"

    def fake_configure_branch_protection(config: e2e.E2EConfig, runner: e2e.Runner) -> None:
        del config, runner
        events.append("branch-protection")
        raise RuntimeError("branch protection failed")

    def fake_cleanup_repo(config: e2e.E2EConfig, runner: e2e.Runner) -> str:
        del runner
        events.append(f"cleanup:{config.full_name}")
        return "deleted"

    monkeypatch.setattr(e2e, "create_repo", fake_create_repo)
    monkeypatch.setattr(e2e, "configure_merge_repo_settings", fake_configure_merge_repo_settings)
    monkeypatch.setattr(e2e, "bootstrap_project", fake_bootstrap_project)
    monkeypatch.setattr(e2e, "configure_branch_protection", fake_configure_branch_protection)
    monkeypatch.setattr(e2e, "cleanup_repo", fake_cleanup_repo)

    with pytest.raises(RuntimeError, match="branch protection failed"):
        e2e.run_e2e(
            {
                "FRONTIER_REAL_GITHUB_E2E": "1",
                "FRONTIER_E2E_OWNER": "owner",
                "FRONTIER_E2E_DELETE_REPO": "1",
            },
            RecordingRunner(),  # type: ignore[arg-type]
        )

    assert events[:4] == ["create", "merge-settings", "bootstrap", "branch-protection"]
    assert len(events) == 5
    assert events[4].startswith("cleanup:owner/frontier-harness-e2e-")


def test_cleanup_refuses_to_delete_repo_outside_fixed_disposable_prefix() -> None:
    runner = RecordingRunner()
    config = make_config(
        repo_prefix="custom-e2e",
        repo_name="custom-e2e-123",
        delete_repo=True,
    )

    with pytest.raises(RuntimeError, match="Refusing to delete repo outside disposable prefix"):
        e2e.cleanup_repo(config, runner)  # type: ignore[arg-type]

    assert not runner.calls


def test_stage_non_ignored_files_uses_explicit_paths(tmp_path: Path) -> None:
    runner = e2e.Runner()
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (tmp_path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    e2e.require_ok(runner.run(["git", "init"], cwd=tmp_path), "git init")

    staged = e2e.stage_non_ignored_files(tmp_path, runner)

    assert staged == [".gitignore", "tracked.txt"]
    diff = runner.run(["git", "diff", "--cached", "--name-only"], cwd=tmp_path)
    assert diff.stdout.splitlines() == [".gitignore", "tracked.txt"]
