import json
from pathlib import Path

import match

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    with open(FIXTURES / name, "r", encoding="utf-8") as f:
        return json.load(f)


def test_apply_matches_increments_existing_topic_on_match():
    registry = load_fixture("registry_sample.json")
    new_topics = load_fixture("new_topics_sample.json")
    decisions = [
        {"index": 0, "matched_id": "t_existing1"},
        {"index": 1, "matched_id": None},
    ]

    result = match.apply_matches(registry, new_topics, decisions, week="2026-W33", id_factory=lambda: "t_new1")

    existing = next(t for t in result["topics"] if t["id"] == "t_existing1")
    assert existing["weekly_mentions"]["2026-W33"] == 1
    assert "https://reddit.com/r/example/comments/new1" in existing["example_permalinks"]


def test_apply_matches_creates_new_topic_on_no_match():
    registry = load_fixture("registry_sample.json")
    new_topics = load_fixture("new_topics_sample.json")
    decisions = [
        {"index": 0, "matched_id": "t_existing1"},
        {"index": 1, "matched_id": None},
    ]

    result = match.apply_matches(registry, new_topics, decisions, week="2026-W33", id_factory=lambda: "t_new1")

    created = next(t for t in result["topics"] if t["id"] == "t_new1")
    assert created["canonical_name"] == "Export to CSV"
    assert created["first_seen_week"] == "2026-W33"
    assert created["weekly_mentions"] == {"2026-W33": 1}
    assert created["example_permalinks"] == ["https://reddit.com/r/example/comments/new2"]


def test_apply_matches_leaves_registry_unchanged_when_no_new_topics():
    registry = load_fixture("registry_sample.json")

    result = match.apply_matches(registry, [], [], week="2026-W33")

    assert len(result["topics"]) == 1
    assert "2026-W33" not in result["topics"][0]["weekly_mentions"]


def test_build_matching_prompt_includes_topic_names():
    existing = load_fixture("registry_sample.json")["topics"]
    new_topics = load_fixture("new_topics_sample.json")

    prompt = match.build_matching_prompt(new_topics, existing)

    assert "Dark mode support" in prompt
    assert "Export to CSV" in prompt
