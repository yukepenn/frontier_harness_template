from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.render_templates import build_context, load_profile, render_tree, repo_root
import pytest

from tools.upgrade_frontier import build_plan, classify, ensure_inside


def render_target(target: Path, project_name: str = "sample_project") -> None:
    profile = load_profile("generic")
    context = build_context(project_name, profile)
    render_tree(repo_root() / "templates", target, context, force=True)


def test_classification_preserves_project_specific_files() -> None:
    assert classify("tools/frontier/ralph_driver.py") == "GENERIC_HARNESS"
    assert classify("campaigns/MY_CAMPAIGN/GOAL.md") == "PROJECT_SPECIFIC"
    assert classify("ACTIVE_CAMPAIGN.md") == "PROJECT_SPECIFIC"
    assert classify("runs/run1/state.json") == "GENERATED_ARTIFACT"


def test_dry_run_reports_changes(tmp_path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    render_target(target)
    (target / "tools/frontier/ralph_driver.py").write_text("# old\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root() / "tools" / "upgrade_frontier.py"),
            "--target",
            str(target),
            "--profile",
            "generic",
            "--project-name",
            "sample_project",
            "--dry-run",
        ],
        cwd=repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "UPDATE [GENERIC_HARNESS] tools/frontier/ralph_driver.py" in result.stdout


def test_apply_updates_generic_and_preserves_campaign(tmp_path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    render_target(target)
    generic_path = target / "tools/frontier/ralph_driver.py"
    generic_path.write_text("# old\n", encoding="utf-8")
    campaign_path = target / "campaigns/G005_WORKFLOW2_TOY/GOAL.md"
    campaign_path.write_text("# project campaign\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root() / "tools" / "upgrade_frontier.py"),
            "--target",
            str(target),
            "--profile",
            "generic",
            "--project-name",
            "sample_project",
            "--apply",
        ],
        cwd=repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert generic_path.read_text(encoding="utf-8") != "# old\n"
    assert campaign_path.read_text(encoding="utf-8") == "# project campaign\n"
    assert (target / ".frontier" / "upgrade_reports").is_dir()


def test_build_plan_refuses_path_traversal(tmp_path) -> None:
    rendered = tmp_path / "rendered"
    target = tmp_path / "target"
    rendered.mkdir()
    target.mkdir()
    (rendered / "README.md").write_text("readme\n", encoding="utf-8")

    plan = build_plan(rendered, target)

    assert plan[0].path == "README.md"
    with pytest.raises(ValueError):
        ensure_inside(target, target / ".." / "outside.txt")
