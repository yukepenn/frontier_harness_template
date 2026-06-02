#!/usr/bin/env python3
"""Optional disposable real-GitHub Workflow 2 E2E for the template source repo."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DISPOSABLE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    return_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.return_code == 0


class Runner:
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
        timeout: int = 600,
    ) -> CommandResult:
        completed = subprocess.run(
            [str(part) for part in command],
            cwd=cwd,
            env=dict(env) if env is not None else None,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(list(map(str, command)), completed.returncode, completed.stdout, completed.stderr)


@dataclass(frozen=True)
class E2EConfig:
    owner: str
    repo_prefix: str
    repo_name: str
    delete_repo: bool
    archive_repo: bool

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo_name}"


def env_flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").lower() in {"1", "true", "yes", "on"}


def load_config(env: Mapping[str, str]) -> E2EConfig:
    if not env_flag(env, "FRONTIER_REAL_GITHUB_E2E"):
        raise RuntimeError("Set FRONTIER_REAL_GITHUB_E2E=1 to run the disposable real-GitHub E2E.")
    owner = env.get("FRONTIER_E2E_OWNER", "").strip()
    if not owner:
        raise RuntimeError("Set FRONTIER_E2E_OWNER to the GitHub user or organization that will own the disposable repo.")
    prefix = env.get("FRONTIER_E2E_REPO_PREFIX", "frontier-harness-e2e").strip()
    if not prefix or not DISPOSABLE_RE.fullmatch(prefix):
        raise RuntimeError("FRONTIER_E2E_REPO_PREFIX must contain only letters, numbers, dot, underscore, or dash.")
    repo_name = f"{prefix}-{int(time.time())}-{os.getpid()}"
    return E2EConfig(
        owner=owner,
        repo_prefix=prefix,
        repo_name=repo_name,
        delete_repo=env_flag(env, "FRONTIER_E2E_DELETE_REPO"),
        archive_repo=env_flag(env, "FRONTIER_E2E_ARCHIVE_REPO"),
    )


def require_ok(result: CommandResult, label: str) -> None:
    if result.ok:
        return
    raise RuntimeError(
        f"{label} failed: {' '.join(result.command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def assert_disposable(config: E2EConfig, repo_name: str | None = None) -> None:
    name = repo_name or config.repo_name
    if not name.startswith(config.repo_prefix + "-"):
        raise RuntimeError(f"Refusing to modify non-disposable repo name: {name}")
    if not DISPOSABLE_RE.fullmatch(name):
        raise RuntimeError(f"Refusing unsafe disposable repo name: {name}")


def create_repo(config: E2EConfig, runner: Runner) -> None:
    assert_disposable(config)
    require_ok(runner.run(["gh", "auth", "status"], cwd=ROOT, timeout=120), "gh auth status")
    require_ok(
        runner.run(
            [
                "gh",
                "repo",
                "create",
                config.full_name,
                "--private",
                "--disable-wiki",
                "--description",
                "Disposable Frontier Harness Workflow2 E2E repository",
            ],
            cwd=ROOT,
            timeout=300,
        ),
        "gh repo create",
    )


def write_e2e_campaign(project: Path) -> str:
    campaign_id = "E2E_WORKFLOW2_GITHUB"
    campaign_dir = project / "campaigns" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    (campaign_dir / "GOAL.md").write_text("# GitHub E2E\n\nExercise disposable Workflow 2 GitHub merge.\n", encoding="utf-8")
    (campaign_dir / "PHASE_PLAN.md").write_text(
        "# Phase Plan\n\n| Phase | Name | Lane | Dependencies |\n| --- | --- | --- | --- |\n| P00 | Disposable GitHub E2E | YELLOW | none |\n",
        encoding="utf-8",
    )
    (campaign_dir / "campaign.yaml").write_text(
        f"""campaign_id: "{campaign_id}"
workflow: "workflow2"
default_lane: "yellow"
limits:
  max_phases: 1
phases:
  - id: "P00"
    name: "Disposable GitHub E2E"
    lane: "YELLOW"
    dependencies: []
""",
        encoding="utf-8",
    )
    for name in ("ACCEPTANCE.md", "RISK_REGISTER.md", "RUNBOOK.md"):
        (campaign_dir / name).write_text(f"# {name}\n\nDisposable GitHub E2E fixture.\n", encoding="utf-8")
    return campaign_id


def git_output(runner: Runner, project: Path, *args: str) -> str:
    result = runner.run(["git", *args], cwd=project, timeout=300)
    require_ok(result, "git " + " ".join(args))
    return result.stdout.strip()


def stage_non_ignored_files(project: Path, runner: Runner) -> list[str]:
    result = runner.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=project, timeout=120)
    require_ok(result, "git ls-files")
    paths = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    for index in range(0, len(paths), 100):
        chunk = paths[index : index + 100]
        if chunk:
            require_ok(runner.run(["git", "add", "--", *chunk], cwd=project, timeout=300), "git add explicit paths")
    return paths


def bootstrap_project(config: E2EConfig, temp_root: Path, runner: Runner) -> tuple[Path, str, str]:
    project = temp_root / config.repo_name
    require_ok(
        runner.run(
            [
                sys.executable,
                str(ROOT / "tools" / "bootstrap_frontier.py"),
                "--target",
                str(project),
                "--profile",
                "generic",
                "--project-name",
                config.repo_name,
                "--force",
            ],
            cwd=ROOT,
            timeout=600,
        ),
        "bootstrap_frontier",
    )
    campaign_id = write_e2e_campaign(project)
    git_output(runner, project, "init", "-b", "main")
    git_output(runner, project, "config", "user.name", "Frontier E2E")
    git_output(runner, project, "config", "user.email", "frontier-e2e@example.invalid")
    git_output(runner, project, "remote", "add", "origin", f"https://github.com/{config.full_name}.git")
    staged = stage_non_ignored_files(project, runner)
    if not staged:
        raise RuntimeError("Rendered project produced no files to stage.")
    git_output(runner, project, "commit", "-m", "test: bootstrap disposable frontier harness")
    git_output(runner, project, "push", "-u", "origin", "main")
    main_sha = git_output(runner, project, "rev-parse", "HEAD")
    return project, campaign_id, main_sha


def configure_branch_protection(config: E2EConfig, runner: Runner) -> None:
    payload = {
        "required_status_checks": {"strict": True, "contexts": ["validate"]},
        "enforce_admins": True,
        "required_pull_request_reviews": None,
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }
    require_ok(
        runner.run(
            [
                "gh",
                "api",
                "--method",
                "PUT",
                f"repos/{config.full_name}/branches/main/protection",
                "--input",
                "-",
            ],
            cwd=ROOT,
            input_text=json.dumps(payload),
            timeout=300,
        ),
        "configure branch protection",
    )


def local_provider_runner_script(campaign_id: str) -> str:
    return f"""
import os
from pathlib import Path
from tools.frontier import ralph_driver

outputs = iter([
    "# Spec\\n\\nCommit-Eligible Allowed Paths:\\n- docs/e2e_workflow2_github.md\\n",
    "# Review\\n\\nVERDICT: PASS\\n",
    "# Done Check\\n\\nDONE_CHECK: PASS\\n",
])

def fake_claude(prompt, root=ralph_driver.ROOT):
    del prompt, root
    return ralph_driver.CommandResult(("claude",), 0, next(outputs), "")

def fake_codex(prompt, root=ralph_driver.ROOT):
    del prompt
    path = Path(root) / "docs" / "e2e_workflow2_github.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("# Disposable GitHub E2E\\n\\nGenerated by local fixture provider.\\n", encoding="utf-8")
    return ralph_driver.CommandResult(("codex", "exec"), 0, "# Executor\\n\\nUpdated docs/e2e_workflow2_github.md.\\n", "")

ralph_driver.claude_headless = fake_claude
ralph_driver.codex_noninteractive = fake_codex
ralph_driver.run_phase_validation = lambda root: (True, "# Validation\\n\\nPassed.\\n")
os.environ["FRONTIER_CREATE_PR"] = "1"
os.environ["FRONTIER_ALLOW_AUTOMERGE"] = "1"
raise SystemExit(ralph_driver.run_campaign("{campaign_id}", None, "yellow", provider_wired=True, max_phases=1))
"""


def run_workflow(project: Path, campaign_id: str, runner: Runner, env: Mapping[str, str]) -> Path:
    result = runner.run(
        [sys.executable, "-c", local_provider_runner_script(campaign_id)],
        cwd=project,
        env={**os.environ, **env, "FRONTIER_CREATE_PR": "1", "FRONTIER_ALLOW_AUTOMERGE": "1"},
        timeout=1800,
    )
    require_ok(result, "local provider Workflow2 run")
    run_dirs = sorted((project / "runs").glob(f"*{campaign_id}*"))
    if not run_dirs:
        raise RuntimeError("Workflow run did not create a run directory.")
    return run_dirs[-1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def phase_dir(run_dir: Path) -> Path:
    phases = sorted((run_dir / "phases").iterdir())
    if not phases:
        raise RuntimeError("Run has no phase directories.")
    return phases[0]


def wait_for_pr_merged(config: E2EConfig, pr_number: int, runner: Runner, timeout_seconds: int = 900) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() <= deadline:
        result = runner.run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--repo",
                config.full_name,
                "--json",
                "state,mergedAt,mergeStateStatus",
            ],
            cwd=ROOT,
            timeout=120,
        )
        require_ok(result, "gh pr view")
        data = json.loads(result.stdout or "{}")
        if str(data.get("state") or "").upper() == "MERGED" or data.get("mergedAt"):
            return True
        time.sleep(15)
    return False


def resume_if_needed(project: Path, run_dir: Path, runner: Runner) -> None:
    state = read_json(run_dir / "state.json")
    phase = state["phases"][0]
    if phase.get("status") in {"PASS", "PASS_WITH_WARNINGS"}:
        return
    result = runner.run(
        [
            sys.executable,
            "tools/frontier/ralph_driver.py",
            "resume",
            "--run-dir",
            str(run_dir),
            "--phase-id",
            str(phase["phase_id"]),
            "--from-stage",
            "merge",
            "--provider-wired",
            "--no-provider-replay",
        ],
        cwd=project,
        env={**os.environ, "FRONTIER_ALLOW_AUTOMERGE": "1"},
        timeout=900,
    )
    require_ok(result, "resume merge stage")


def cleanup_repo(config: E2EConfig, runner: Runner) -> str:
    assert_disposable(config)
    if config.delete_repo:
        require_ok(runner.run(["gh", "repo", "delete", config.full_name, "--yes"], cwd=ROOT, timeout=300), "delete repo")
        return "deleted"
    if config.archive_repo:
        require_ok(runner.run(["gh", "repo", "archive", config.full_name, "--yes"], cwd=ROOT, timeout=300), "archive repo")
        return "archived"
    return "left in place"


def run_e2e(env: Mapping[str, str], runner: Runner | None = None) -> dict[str, object]:
    config = load_config(env)
    runner = runner or Runner()
    with tempfile.TemporaryDirectory(prefix="frontier-real-github-e2e-") as tmp:
        temp_root = Path(tmp)
        create_repo(config, runner)
        cleanup_action = "left in place"
        try:
            project, campaign_id, before_sha = bootstrap_project(config, temp_root, runner)
            configure_branch_protection(config, runner)
            run_dir = run_workflow(project, campaign_id, runner, env)
            pdir = phase_dir(run_dir)
            pr_create = read_json(pdir / "pr_create.json")
            metadata = pr_create.get("metadata") if isinstance(pr_create.get("metadata"), dict) else {}
            nested_pr = metadata.get("pr") if isinstance(metadata.get("pr"), dict) else {}
            pr_number = int(metadata.get("number") or nested_pr.get("number"))
            if not wait_for_pr_merged(config, pr_number, runner):
                raise RuntimeError(f"PR {pr_number} did not merge before timeout.")
            resume_if_needed(project, run_dir, runner)
            after_sha = git_output(runner, project, "rev-parse", "origin/main")
            if after_sha == before_sha:
                raise RuntimeError("origin/main did not advance after merge.")
            cleanup_action = cleanup_repo(config, runner)
            summary = {
                "repo": config.full_name,
                "pr_number": pr_number,
                "merged": True,
                "main_before": before_sha,
                "main_after": after_sha,
                "cleanup": cleanup_action,
            }
            summary_path = temp_root / "E2E_SUMMARY.md"
            summary_path.write_text(
                "\n".join(
                    [
                        "# E2E Summary",
                        "",
                        f"Repo: {config.full_name}",
                        f"PR: {pr_number}",
                        "Merged: true",
                        f"Main before: {before_sha}",
                        f"Main after: {after_sha}",
                        f"Cleanup: {cleanup_action}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            print(summary_path.read_text(encoding="utf-8"))
            return summary
        finally:
            if cleanup_action == "left in place" and (config.delete_repo or config.archive_repo):
                cleanup_repo(config, runner)


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        summary = run_e2e(os.environ)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
