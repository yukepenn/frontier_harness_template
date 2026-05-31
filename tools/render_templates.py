"""Render Frontier Harness templates with a small stdlib-only renderer."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

TEMPLATE_VERSION = "3.0.0"
VARIABLE_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*}}")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_scalar(value: str) -> str | bool | int:
    value = value.strip()
    if not value:
        return ""
    if value[0] == value[-1] and value.startswith(("'", '"')):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def load_profile(profile_name: str, profiles_dir: Path | None = None) -> dict[str, Any]:
    """Load the simple key/value YAML profile format used by this template."""

    profiles_dir = profiles_dir or repo_root() / "profiles"
    path = profiles_dir / f"{profile_name}.yaml"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in profiles_dir.glob("*.yaml")))
        raise FileNotFoundError(f"Unknown profile '{profile_name}'. Available profiles: {available}")

    data: dict[str, Any] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid profile line {path}:{line_number}: {raw_line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid empty profile key at {path}:{line_number}")
        data[key] = parse_scalar(value)

    if data.get("name") != profile_name:
        raise ValueError(f"Profile {path} must declare name: {profile_name}")
    return data


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return slug or "frontier-project"


def build_context(project_name: str, profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_name": project_name,
        "project_slug": slugify(project_name),
        "profile_name": str(profile["name"]),
        "profile": profile,
        "template_version": TEMPLATE_VERSION,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def resolve_value(context: dict[str, Any], expression: str) -> Any:
    value: Any = context
    for part in expression.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise KeyError(f"Unknown template variable: {expression}")
    return value


def render_string(template: str, context: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = resolve_value(context, match.group(1))
        return str(value).lower() if isinstance(value, bool) else str(value)

    rendered = VARIABLE_RE.sub(replace, template)
    return Template(rendered).safe_substitute(
        {
            "project_name": context["project_name"],
            "project_slug": context["project_slug"],
            "profile_name": context["profile_name"],
            "template_version": context["template_version"],
        }
    )


def destination_for(source: Path, templates_dir: Path, target_dir: Path) -> Path:
    relative = source.relative_to(templates_dir)
    if relative.suffix == ".j2":
        relative = relative.with_suffix("")
    destination = (target_dir / relative).resolve()
    target_resolved = target_dir.resolve()
    if destination != target_resolved and target_resolved not in destination.parents:
        raise ValueError(f"Refusing to write outside target: {destination}")
    return destination


def iter_template_files(templates_dir: Path) -> list[Path]:
    return sorted(path for path in templates_dir.rglob("*") if path.is_file())


def render_tree(
    templates_dir: Path,
    target_dir: Path,
    context: dict[str, Any],
    *,
    force: bool = False,
) -> list[Path]:
    templates_dir = templates_dir.resolve()
    target_dir = target_dir.resolve()
    files = iter_template_files(templates_dir)
    destinations = [destination_for(source, templates_dir, target_dir) for source in files]
    existing = [path for path in destinations if path.exists()]
    if existing and not force:
        joined = "\n".join(str(path) for path in existing)
        raise FileExistsError(f"Refusing to overwrite existing files without --force:\n{joined}")

    written: list[Path] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for source, destination in zip(files, destinations, strict=True):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".j2":
            rendered = render_string(source.read_text(encoding="utf-8"), context)
            destination.write_text(rendered, encoding="utf-8")
        else:
            shutil.copyfile(source, destination)
        if destination.suffix == ".sh" or ".githooks" in destination.parts:
            destination.chmod(destination.stat().st_mode | 0o111)
        written.append(destination)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Frontier Harness .j2 templates.")
    parser.add_argument("--templates-dir", type=Path, default=repo_root() / "templates")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--profile", default="generic")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    context = build_context(args.project_name, profile)
    written = render_tree(args.templates_dir, args.target, context, force=args.force)
    print(f"Rendered {len(written)} files into {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
