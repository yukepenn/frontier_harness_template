"""Safely upgrade an existing repo from this Frontier Harness template."""

from __future__ import annotations

import argparse
import filecmp
import fnmatch
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    from render_templates import build_context, load_profile, render_tree, repo_root
except ModuleNotFoundError:
    from tools.render_templates import build_context, load_profile, render_tree, repo_root


GENERIC_HARNESS_PATTERNS = [
    ".codex/**",
    ".claude/skills/frontier-*/**",
    ".claude/agents/**",
    ".claude/rules/**",
    ".claude/hooks/**",
    ".claude/settings.json",
    ".githooks/**",
    ".github/workflows/frontier-*.yml",
    ".github/pull_request_template.md",
    "tools/frontier/**",
    "tools/hooks/**",
    "tools/verify.py",
    "scripts/ralph/**",
    "evals/canaries/**",
    "evals/behaviors/**",
    "tests/test_ralph_driver.py",
    "tests/test_command_runner.py",
    "tests/test_provider_adapters.py",
    "tests/test_state_machine.py",
    "tests/test_verdict.py",
    "tests/test_worktree_manager.py",
    "tests/test_merge_gate.py",
    "tests/test_github_utils.py",
    "tests/test_canaries.py",
    "tests/test_hooks.py",
    "tests/test_frontier_config.py",
    "docs/workflow.md",
    "docs/validation.md",
    "docs/operations.md",
    "docs/model_routing.md",
    "docs/automation_lanes.md",
    "docs/campaign_authoring.md",
    "justfile",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
]

PROJECT_SPECIFIC_PATTERNS = [
    "ACTIVE_CAMPAIGN.md",
    "PROJECT_STATUS.md",
    "PROGRESS.md",
    "frontier.yaml",
    ".claude/skills/project-skill/**",
    "campaigns/**",
    "docs/architecture.md",
    "docs/artifact_policy.md",
    "src/**",
    "configs/**",
    "tests/project_*/**",
    "tests/project-specific/**",
    "data/**",
    "artifacts/**",
    "runs/**",
]

GENERATED_ARTIFACT_PATTERNS = [
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
    "**/.mypy_cache/**",
    "node_modules/**",
    ".venv/**",
    "runs/**",
    "artifacts/**",
]


@dataclass(frozen=True)
class FilePlan:
    path: str
    classification: str
    action: str


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def classify(path: str) -> str:
    if matches(path, GENERATED_ARTIFACT_PATTERNS):
        return "GENERATED_ARTIFACT"
    if matches(path, PROJECT_SPECIFIC_PATTERNS):
        return "PROJECT_SPECIFIC"
    if matches(path, GENERIC_HARNESS_PATTERNS):
        return "GENERIC_HARNESS"
    return "UNKNOWN"


def ensure_inside(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"Refusing path traversal outside target: {candidate}")
    return resolved


def render_temp(profile_name: str, project_name: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmp = tempfile.TemporaryDirectory(prefix="frontier-upgrade-")
    rendered = Path(tmp.name) / "rendered"
    root = repo_root()
    profile = load_profile(profile_name, root / "profiles")
    context = build_context(project_name, profile)
    render_tree(root / "templates", rendered, context, force=True)
    return tmp, rendered


def build_plan(rendered: Path, target: Path) -> list[FilePlan]:
    plan: list[FilePlan] = []
    for source in sorted(path for path in rendered.rglob("*") if path.is_file()):
        relative = rel(source, rendered)
        classification = classify(relative)
        destination = ensure_inside(target, target / relative)
        if not destination.exists():
            action = "CREATE"
        elif filecmp.cmp(source, destination, shallow=False):
            action = "UNCHANGED"
        elif classification == "GENERIC_HARNESS":
            action = "UPDATE"
        elif classification == "PROJECT_SPECIFIC":
            action = "PRESERVE_PROJECT"
        elif classification == "GENERATED_ARTIFACT":
            action = "PRESERVE_ARTIFACT"
        else:
            action = "REPORT_CONFLICT"
        plan.append(FilePlan(relative, classification, action))
    return plan


def apply_plan(rendered: Path, target: Path, plan: list[FilePlan], *, force_project_files: bool) -> list[str]:
    applied: list[str] = []
    for item in plan:
        if item.action == "UNCHANGED":
            continue
        if item.classification == "GENERIC_HARNESS" or (
            force_project_files and item.classification == "PROJECT_SPECIFIC"
        ):
            source = rendered / item.path
            destination = ensure_inside(target, target / item.path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            applied.append(item.path)
    return applied


def report(plan: list[FilePlan], applied: list[str] | None = None) -> str:
    lines = [
        "# Frontier Upgrade Report",
        "",
        f"Generated at: {datetime.now(UTC).replace(microsecond=0).isoformat()}",
        "",
        "## Summary",
        "",
    ]
    counts: dict[str, int] = {}
    for item in plan:
        counts[item.action] = counts.get(item.action, 0) + 1
    for action in sorted(counts):
        lines.append(f"- {action}: {counts[action]}")
    if applied is not None:
        lines.append(f"- APPLIED: {len(applied)}")
    lines.extend(["", "## Files", ""])
    for item in plan:
        lines.append(f"- {item.action} [{item.classification}] {item.path}")
    if applied:
        lines.extend(["", "## Applied", ""])
        lines.extend(f"- {path}" for path in applied)
    return "\n".join(lines) + "\n"


def write_report(target: Path, text: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_dir = target / ".frontier" / "upgrade_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{stamp}.md"
    path.write_text(text, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upgrade generic Frontier Harness files in a target repo.")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--project-name", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--force-project-files", action="store_true")
    args = parser.parse_args(argv)

    target = args.target.resolve()
    if not target.exists():
        print(f"Target does not exist: {target}", file=sys.stderr)
        return 2
    tmp, rendered = render_temp(args.profile, args.project_name)
    try:
        plan = build_plan(rendered, target)
        applied: list[str] | None = None
        if args.apply:
            applied = apply_plan(rendered, target, plan, force_project_files=args.force_project_files)
        text = report(plan, applied)
        if args.apply:
            path = write_report(target, text)
            print(f"Wrote upgrade report: {path}")
        else:
            print(text, end="")
    finally:
        tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
