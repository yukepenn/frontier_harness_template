"""Bootstrap a project from the Frontier Harness template."""

from __future__ import annotations

import argparse
from pathlib import Path

from render_templates import build_context, load_profile, render_tree, repo_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a Frontier Harness into a target repo.")
    parser.add_argument("--target", type=Path, required=True, help="Directory to render into.")
    parser.add_argument("--profile", required=True, help="Profile name from profiles/<name>.yaml.")
    parser.add_argument("--project-name", required=True, help="Human-readable project name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    args = parser.parse_args(argv)

    root = repo_root()
    profile = load_profile(args.profile, root / "profiles")
    context = build_context(args.project_name, profile)
    written = render_tree(root / "templates", args.target, context, force=args.force)
    print(f"Bootstrapped {args.project_name} with profile {args.profile}: {len(written)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
