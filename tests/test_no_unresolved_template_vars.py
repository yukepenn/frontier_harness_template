import re
from pathlib import Path

from tools.render_templates import build_context, load_profile, render_tree, repo_root

UNRESOLVED_RE = re.compile(r"({{.*?}}|{%.*?%})", re.DOTALL)


def test_rendered_profiles_have_no_unresolved_template_variables(tmp_path: Path) -> None:
    for profile_path in (repo_root() / "profiles").glob("*.yaml"):
        profile = load_profile(profile_path.stem)
        context = build_context(f"{profile_path.stem}_project", profile)
        target = tmp_path / profile_path.stem

        render_tree(repo_root() / "templates", target, context)

        for path in target.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                assert not UNRESOLVED_RE.search(text), path
