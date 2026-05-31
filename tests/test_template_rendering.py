from pathlib import Path

import pytest

from tools.render_templates import build_context, load_profile, render_tree, repo_root


def test_render_tree_writes_expected_files(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    written = render_tree(repo_root() / "templates", tmp_path, context)

    assert written
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / "frontier.yaml").is_file()
    assert (tmp_path / "campaigns").is_dir()
    assert (tmp_path / "specs").is_dir()
    assert (tmp_path / "handoffs").is_dir()
    assert (tmp_path / "reviews").is_dir()
    assert not any(path.name.endswith(".j2") for path in tmp_path.rglob("*"))


def test_render_tree_refuses_overwrite_without_force(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)

    with pytest.raises(FileExistsError):
        render_tree(repo_root() / "templates", tmp_path, context)


def test_render_tree_allows_force_overwrite(tmp_path: Path) -> None:
    profile = load_profile("generic")
    context = build_context("sample_project", profile)

    render_tree(repo_root() / "templates", tmp_path, context)
    render_tree(repo_root() / "templates", tmp_path, context, force=True)

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8").startswith("# sample_project")
