import json
import os
import uuid
from datetime import date

import anthropic

from credentials import get_secret
from registry import load_registry, save_registry
from weekutil import iso_week_string

MATCH_MODEL = "claude-sonnet-5"

MATCHING_PROMPT_TEMPLATE = """You are matching newly observed product feedback topics against a \
canonical registry of existing topics for the same product.

Existing canonical topics:
{existing_topics_json}

New topics observed this week:
{new_topics_json}

For each new topic (by its "index"), decide whether it is semantically the same as one \
of the existing canonical topics, or a genuinely new topic.

Respond with ONLY a JSON array, one object per new topic, in the same order as given:
[{{"index": 0, "matched_id": "t_001"}}, {{"index": 1, "matched_id": null}}]

Use "matched_id": null when the topic is new. Only match if the topics are truly about \
the same underlying subject, not just the same category.
"""


class MatchError(Exception):
    pass


def build_matching_prompt(new_topics, existing_topics):
    existing_summary = [
        {"id": t["id"], "canonical_name": t["canonical_name"], "description": t["description"]}
        for t in existing_topics
    ]
    new_summary = [
        {"index": i, "topic": t["topic"], "description": t["description"]}
        for i, t in enumerate(new_topics)
    ]
    return MATCHING_PROMPT_TEMPLATE.format(
        existing_topics_json=json.dumps(existing_summary, indent=2),
        new_topics_json=json.dumps(new_summary, indent=2),
    )


def _call_matcher(client, new_topics, existing_topics):
    if not new_topics:
        return []

    prompt = build_matching_prompt(new_topics, existing_topics)
    try:
        response = client.messages.create(
            model=MATCH_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text)
    except Exception as e:
        raise MatchError(f"matching call failed: {e}") from e


def _default_id_factory():
    return f"t_{uuid.uuid4().hex[:8]}"


def apply_matches(registry, new_topics, decisions, week, id_factory=_default_id_factory):
    topics_by_id = {t["id"]: t for t in registry["topics"]}
    decisions_by_index = {d["index"]: d["matched_id"] for d in decisions}

    for i, new_topic in enumerate(new_topics):
        matched_id = decisions_by_index.get(i)

        if matched_id and matched_id in topics_by_id:
            topic = topics_by_id[matched_id]
            topic["weekly_mentions"][week] = topic["weekly_mentions"].get(week, 0) + 1
            topic["example_permalinks"].append(new_topic["permalink"])
        else:
            new_id = id_factory()
            topic = {
                "id": new_id,
                "canonical_name": new_topic["topic"],
                "description": new_topic["description"],
                "category": new_topic["category"],
                "first_seen_week": week,
                "weekly_mentions": {week: 1},
                "example_permalinks": [new_topic["permalink"]],
            }
            registry["topics"].append(topic)
            topics_by_id[new_id] = topic

    return registry


def run(extracted_dir="data/extracted", registry_path="data/registry.json", today=None, client=None):
    week = iso_week_string(today or date.today())
    extracted_path = os.path.join(extracted_dir, f"{week}.json")

    new_topics = []
    if os.path.exists(extracted_path):
        with open(extracted_path, "r", encoding="utf-8") as f:
            new_topics = json.load(f)

    registry = load_registry(registry_path)
    client = client or anthropic.Anthropic(api_key=get_secret("anthropic_api_key"))
    decisions = _call_matcher(client, new_topics, registry["topics"])
    registry = apply_matches(registry, new_topics, decisions, week)
    save_registry(registry_path, registry)


if __name__ == "__main__":
    run()
