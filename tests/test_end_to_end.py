import csv
import json
from datetime import date

import extract
import fetch
import match
import report
from registry import load_registry


class FakeSubmission:
    def __init__(self, fullname, id, title, selftext, permalink, score, num_comments, created_utc):
        self.fullname = fullname
        self.id = id
        self.title = title
        self.selftext = selftext
        self.permalink = permalink
        self.score = score
        self.num_comments = num_comments
        self.created_utc = created_utc


class FakeSubreddit:
    def __init__(self, submissions):
        self._submissions = submissions

    def new(self, limit):
        return iter(self._submissions[:limit])


class FakeRedditClient:
    def __init__(self, subreddits):
        self._subreddits = subreddits

    def subreddit(self, name):
        return self._subreddits[name]


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
        return FakeResponse(self._responses.pop(0))


class FakeAnthropicClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def test_full_pipeline_from_fetch_to_report(tmp_path):
    reddit_client = FakeRedditClient({
        "yourproductname": FakeSubreddit([
            FakeSubmission(
                fullname="t3_p1", id="p1", title="Please add dark mode",
                selftext="Would love a dark theme", permalink="/r/yourproductname/comments/p1",
                score=20, num_comments=4, created_utc=1700000000.0,
            ),
        ]),
    })

    extract_client = FakeAnthropicClient([
        json.dumps({"topic": "Dark mode support", "description": "User wants dark theme", "category": "feature_request"}),
    ])
    match_client = FakeAnthropicClient([
        json.dumps([{"index": 0, "matched_id": None}]),
    ])

    state_path = tmp_path / "state.json"
    raw_dir = tmp_path / "raw"
    extracted_dir = tmp_path / "extracted"
    registry_path = tmp_path / "registry.json"
    report_dir = tmp_path / "reports"
    today = date(2026, 8, 15)

    fetch.run(
        subreddits=["yourproductname"], fetch_limit_per_subreddit=10,
        state_path=str(state_path), raw_dir=str(raw_dir), today=today, reddit_client=reddit_client,
    )
    extract.run(raw_dir=str(raw_dir), out_dir=str(extracted_dir), today=today, client=extract_client)
    match.run(extracted_dir=str(extracted_dir), registry_path=str(registry_path), today=today, client=match_client)
    report.run(registry_path=str(registry_path), report_dir=str(report_dir), trend_window_weeks=8, today=today)

    registry = load_registry(str(registry_path))
    assert registry["topics"][0]["canonical_name"] == "Dark mode support"
    assert registry["topics"][0]["weekly_mentions"]["2026-W33"] == 1

    with open(report_dir / "2026-W33.json", "r", encoding="utf-8") as f:
        report_rows = json.load(f)
    assert report_rows[0]["canonical_name"] == "Dark mode support"
    assert report_rows[0]["trend"] == "new"

    with open(report_dir / "2026-W33.csv", "r", encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert csv_rows[0]["canonical_name"] == "Dark mode support"
