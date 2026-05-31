"""Preview future Frontier Harness upgrade flow.

G001 intentionally does not rewrite existing projects. This command exists so
automation can discover the future entry point without import failures.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TODO: upgrade a target repo from this template.")
    parser.add_argument("--target", help="Target repo to upgrade.")
    parser.add_argument("--profile", default="generic", help="Profile to render.")
    parser.add_argument("--dry-run", action="store_true", help="Reserved for the future upgrade flow.")
    parser.parse_args(argv)
    print("TODO: template upgrades are not implemented in G001.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
