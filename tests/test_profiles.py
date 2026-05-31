from tools.render_templates import load_profile, repo_root


EXPECTED_PROFILES = {
    "generic",
    "software",
    "research",
    "trading_research",
    "trading_broker",
    "data_pipeline",
    "docs_writing",
    "infra",
}


def test_expected_profiles_exist() -> None:
    profile_names = {path.stem for path in (repo_root() / "profiles").glob("*.yaml")}
    assert profile_names == EXPECTED_PROFILES


def test_profiles_have_required_fields() -> None:
    for name in EXPECTED_PROFILES:
        profile = load_profile(name)
        assert profile["name"] == name
        assert profile["description"]
        assert profile["default_branch"]
        assert profile["automation_lane"]
        assert isinstance(profile["requires_human_review"], bool)
        assert isinstance(profile["trading_enabled"], bool)
        assert isinstance(profile["broker_enabled"], bool)
