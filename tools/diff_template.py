"""Preview future template drift checks.

G001 keeps this command importable and documented. A later goal can compare a
rendered template plan with an existing target repository.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TODO: diff a target repo against this template.")
    parser.add_argument("--target", help="Target repo to inspect.")
    parser.add_argument("--profile", default="generic", help="Profile to compare.")
    parser.parse_args(argv)
    print("TODO: template diffing is not implemented in G001.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
