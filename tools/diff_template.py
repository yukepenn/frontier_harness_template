"""Diff a target repo against the rendered Frontier Harness template."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from upgrade_frontier import build_plan, render_temp, report
except ModuleNotFoundError:
    from tools.upgrade_frontier import build_plan, render_temp, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview template drift for a target repo.")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--profile", default="generic")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args(argv)

    tmp, rendered = render_temp(args.profile, args.project_name)
    try:
        print(
            report(build_plan(rendered, args.target.resolve(), include=args.include, exclude=args.exclude)),
            end="",
        )
    finally:
        tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
