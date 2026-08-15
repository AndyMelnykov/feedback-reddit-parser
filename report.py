import csv
import json
import os
from datetime import date

from registry import load_registry
from weekutil import iso_week_string

TREND_NEW = "new"
TREND_RISING = "rising"
TREND_STABLE = "stable"
TREND_FALLING = "falling"

RISING_THRESHOLD = 1.2
FALLING_THRESHOLD = 0.8

REPORT_FIELDNAMES = ["id", "canonical_name", "category", "mentions_this_week", "total_mentions", "trend"]


def _recent_average(weekly_mentions, current_week, trend_window_weeks):
    past_weeks = sorted(w for w in weekly_mentions if w < current_week)
    recent_weeks = past_weeks[-trend_window_weeks:]
    if not recent_weeks:
        return 0.0
    return sum(weekly_mentions[w] for w in recent_weeks) / len(recent_weeks)


def _trend_direction(mentions_this_week, recent_average, first_seen_week, current_week):
    if first_seen_week == current_week:
        return TREND_NEW
    if recent_average == 0:
        return TREND_RISING if mentions_this_week > 0 else TREND_STABLE
    if mentions_this_week > recent_average * RISING_THRESHOLD:
        return TREND_RISING
    if mentions_this_week < recent_average * FALLING_THRESHOLD:
        return TREND_FALLING
    return TREND_STABLE


def compute_trends(registry, current_week, trend_window_weeks):
    rows = []
    for topic in registry["topics"]:
        weekly = topic["weekly_mentions"]
        mentions_this_week = weekly.get(current_week, 0)
        recent_average = _recent_average(weekly, current_week, trend_window_weeks)

        rows.append({
            "id": topic["id"],
            "canonical_name": topic["canonical_name"],
            "category": topic["category"],
            "mentions_this_week": mentions_this_week,
            "total_mentions": sum(weekly.values()),
            "trend": _trend_direction(mentions_this_week, recent_average, topic["first_seen_week"], current_week),
        })

    rows.sort(key=lambda r: r["mentions_this_week"], reverse=True)
    return rows


def write_report(rows, json_path, csv_path):
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def run(registry_path="data/registry.json", report_dir="data/reports", trend_window_weeks=8, today=None):
    week = iso_week_string(today or date.today())
    registry = load_registry(registry_path)
    rows = compute_trends(registry, week, trend_window_weeks)
    write_report(rows, os.path.join(report_dir, f"{week}.json"), os.path.join(report_dir, f"{week}.csv"))


if __name__ == "__main__":
    run()
