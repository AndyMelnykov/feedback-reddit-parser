import csv
import json

import report


def make_registry(topics):
    return {"topics": topics}


def test_compute_trends_marks_first_seen_this_week_as_new():
    registry = make_registry([{
        "id": "t_1", "canonical_name": "New topic", "category": "feature_request",
        "first_seen_week": "2026-W33", "weekly_mentions": {"2026-W33": 1},
        "example_permalinks": [],
    }])

    rows = report.compute_trends(registry, "2026-W33", trend_window_weeks=8)

    assert rows[0]["trend"] == "new"
    assert rows[0]["mentions_this_week"] == 1


def test_compute_trends_marks_rising_when_above_recent_average():
    registry = make_registry([{
        "id": "t_1", "canonical_name": "Dark mode", "category": "feature_request",
        "first_seen_week": "2026-W30",
        "weekly_mentions": {"2026-W30": 2, "2026-W31": 2, "2026-W32": 2, "2026-W33": 10},
        "example_permalinks": [],
    }])

    rows = report.compute_trends(registry, "2026-W33", trend_window_weeks=8)

    assert rows[0]["trend"] == "rising"


def test_compute_trends_marks_falling_when_below_recent_average():
    registry = make_registry([{
        "id": "t_1", "canonical_name": "Dark mode", "category": "feature_request",
        "first_seen_week": "2026-W30",
        "weekly_mentions": {"2026-W30": 10, "2026-W31": 10, "2026-W32": 10, "2026-W33": 1},
        "example_permalinks": [],
    }])

    rows = report.compute_trends(registry, "2026-W33", trend_window_weeks=8)

    assert rows[0]["trend"] == "falling"


def test_compute_trends_marks_stable_within_band():
    registry = make_registry([{
        "id": "t_1", "canonical_name": "Dark mode", "category": "feature_request",
        "first_seen_week": "2026-W30",
        "weekly_mentions": {"2026-W30": 5, "2026-W31": 5, "2026-W32": 5, "2026-W33": 5},
        "example_permalinks": [],
    }])

    rows = report.compute_trends(registry, "2026-W33", trend_window_weeks=8)

    assert rows[0]["trend"] == "stable"


def test_compute_trends_weights_recent_weeks_more_heavily():
    # Mentions are declining (10 -> 3 -> 1) heading into this week's 3.
    # Flat average = (10+3+1)/3 = 4.67, so 3 < 4.67*0.8 = 3.73 => falling.
    # Linearly-weighted average = (1*10+2*3+3*1)/6 = 3.17, so 3 falls
    # within the stable band (2.53..3.8) once recent weeks count more.
    registry = make_registry([{
        "id": "t_1", "canonical_name": "Dark mode", "category": "feature_request",
        "first_seen_week": "2026-W29",
        "weekly_mentions": {"2026-W30": 10, "2026-W31": 3, "2026-W32": 1, "2026-W33": 3},
        "example_permalinks": [],
    }])

    rows = report.compute_trends(registry, "2026-W33", trend_window_weeks=8)

    assert rows[0]["trend"] == "stable"


def test_compute_trends_sorts_by_mentions_this_week_descending():
    registry = make_registry([
        {"id": "t_low", "canonical_name": "Low", "category": "question",
         "first_seen_week": "2026-W33", "weekly_mentions": {"2026-W33": 1}, "example_permalinks": []},
        {"id": "t_high", "canonical_name": "High", "category": "question",
         "first_seen_week": "2026-W33", "weekly_mentions": {"2026-W33": 9}, "example_permalinks": []},
    ])

    rows = report.compute_trends(registry, "2026-W33", trend_window_weeks=8)

    assert [r["id"] for r in rows] == ["t_high", "t_low"]


def test_write_report_produces_matching_json_and_csv(tmp_path):
    rows = [{
        "id": "t_1", "canonical_name": "Dark mode", "category": "feature_request",
        "mentions_this_week": 5, "total_mentions": 12, "trend": "rising",
    }]
    json_path = tmp_path / "reports" / "2026-W33.json"
    csv_path = tmp_path / "reports" / "2026-W33.csv"

    report.write_report(rows, str(json_path), str(csv_path))

    with open(json_path, "r", encoding="utf-8") as f:
        assert json.load(f) == rows

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = list(csv.DictReader(f))
    assert reader[0]["canonical_name"] == "Dark mode"
    assert reader[0]["trend"] == "rising"
