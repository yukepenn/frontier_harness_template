import re

from tools.render_templates import repo_root


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SKIP_PARTS = {".git", ".tmp", ".pytest_cache", "__pycache__"}


def test_repository_text_is_english_only() -> None:
    for path in repo_root().rglob("*"):
        if SKIP_PARTS.intersection(path.parts) or path.is_dir():
            continue
        if path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not CJK_RE.search(text), path
