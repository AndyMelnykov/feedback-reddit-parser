import json
import os
from datetime import date

import pytest

import extract


class FakeContentBlock:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeContentBlock(text)]


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)

    def create(self, **kwargs):
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


SAMPLE_POST = {
    "id": "abc123",
    "title": "Would love dark mode",
    "selftext": "Please add a dark theme, my eyes hurt at night.",
    "permalink": "/r/test/comments/abc123",
    "score": 42,
    "num_comments": 5,
    "created_utc": 1700000000.0,
}


def test_extract_topic_parses_valid_response():
    client = FakeClient([
        json.dumps({
            "topic": "Dark mode support",
            "description": "User wants a dark theme",
            "category": "feature_request",
        })
    ])

    result = extract.extract_topic(client, SAMPLE_POST)

    assert result == {
        "post_id": "abc123",
        "permalink": "/r/test/comments/abc123",
        "score": 42,
        "num_comments": 5,
        "topic": "Dark mode support",
        "description": "User wants a dark theme",
        "category": "feature_request",
    }


def test_extract_topic_returns_none_on_skip_flag():
    client = FakeClient([json.dumps({"skip": True})])

    assert extract.extract_topic(client, SAMPLE_POST) is None


def test_extract_topic_raises_on_invalid_category():
    client = FakeClient([
        json.dumps({"topic": "x", "description": "y", "category": "not_a_real_category"})
    ])

    with pytest.raises(extract.ExtractionError):
        extract.extract_topic(client, SAMPLE_POST)


def test_extract_topic_raises_on_malformed_json():
    client = FakeClient(["not json at all"])

    with pytest.raises(extract.ExtractionError):
        extract.extract_topic(client, SAMPLE_POST)


def test_extract_topic_raises_on_api_error():
    client = FakeClient([RuntimeError("rate limited")])

    with pytest.raises(extract.ExtractionError):
        extract.extract_topic(client, SAMPLE_POST)


def test_run_skips_bad_post_and_keeps_good_ones(tmp_path):
    week_raw_dir = tmp_path / "raw" / "2026-W33"
    week_raw_dir.mkdir(parents=True)
    with open(week_raw_dir / "sub.json", "w", encoding="utf-8") as f:
        json.dump([SAMPLE_POST, {**SAMPLE_POST, "id": "bad1"}], f)

    client = FakeClient([
        json.dumps({"topic": "Dark mode support", "description": "d", "category": "feature_request"}),
        "not json",
    ])

    out_dir = tmp_path / "extracted"
    extract.run(raw_dir=str(tmp_path / "raw"), out_dir=str(out_dir), today=date(2026, 8, 15), client=client)

    with open(out_dir / "2026-W33.json", "r", encoding="utf-8") as f:
        extracted = json.load(f)

    assert len(extracted) == 1
    assert extracted[0]["post_id"] == "abc123"
