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


def test_real_github_e2e_requires_env_gate() -> None:
    with pytest.raises(RuntimeError, match="FRONTIER_REAL_GITHUB_E2E=1"):
        e2e.load_config({})


def test_disposable_repo_guard_rejects_non_prefix() -> None:
    config = e2e.E2EConfig(
        owner="owner",
        repo_prefix="frontier-harness-e2e",
        repo_name="frontier-harness-e2e-123",
        delete_repo=False,
        archive_repo=False,
    )

    with pytest.raises(RuntimeError, match="non-disposable"):
        e2e.assert_disposable(config, "production-repo")


def test_branch_protection_payload_keeps_validate_and_admin_enforcement() -> None:
    runner = RecordingRunner()
    config = e2e.E2EConfig(
        owner="owner",
        repo_prefix="frontier-harness-e2e",
        repo_name="frontier-harness-e2e-123",
        delete_repo=False,
        archive_repo=False,
    )

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
