import json
import os
from datetime import date

import anthropic

from credentials import get_secret
from weekutil import iso_week_string

VALID_CATEGORIES = {
    "feature_request",
    "complaint",
    "praise",
    "question",
    "competitor_comparison",
}

EXTRACTION_MODEL = "claude-sonnet-5"

EXTRACTION_PROMPT_TEMPLATE = """You are analyzing a Reddit post about a software product for product \
feedback signal extraction.

Post title: {title}
Post body: {selftext}

Respond with ONLY a JSON object with these exact keys:
- "topic": a short topic name (3-6 words)
- "description": a one-line description of what's being said
- "category": one of "feature_request", "complaint", "praise", "question", "competitor_comparison"

If the post is not meaningful product feedback (spam, off-topic, low-effort, or clearly \
AI-generated filler), respond with exactly: {{"skip": true}}
"""


class ExtractionError(Exception):
    pass


def build_extraction_prompt(post: dict) -> str:
    return EXTRACTION_PROMPT_TEMPLATE.format(title=post["title"], selftext=post["selftext"])


def extract_topic(client, post: dict):
    prompt = build_extraction_prompt(post)

    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
    except Exception as e:
        raise ExtractionError(f"post {post['id']}: API call failed: {e}") from e

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"post {post['id']}: non-JSON response: {raw_text!r}") from e

    if parsed.get("skip"):
        return None

    missing = {"topic", "description", "category"} - parsed.keys()
    if missing:
        raise ExtractionError(f"post {post['id']}: response missing keys {missing}")

    if parsed["category"] not in VALID_CATEGORIES:
        raise ExtractionError(f"post {post['id']}: invalid category {parsed['category']!r}")

    return {
        "post_id": post["id"],
        "permalink": post["permalink"],
        "score": post["score"],
        "num_comments": post["num_comments"],
        "topic": parsed["topic"],
        "description": parsed["description"],
        "category": parsed["category"],
    }


def run(raw_dir="data/raw", out_dir="data/extracted", today=None, client=None):
    client = client or anthropic.Anthropic(api_key=get_secret("anthropic_api_key"))
    week = iso_week_string(today or date.today())
    week_raw_dir = os.path.join(raw_dir, week)

    extracted = []
    if os.path.isdir(week_raw_dir):
        for filename in sorted(os.listdir(week_raw_dir)):
            with open(os.path.join(week_raw_dir, filename), "r", encoding="utf-8") as f:
                posts = json.load(f)
            for post in posts:
                try:
                    result = extract_topic(client, post)
                except ExtractionError as e:
                    print(f"skipping post due to extraction error: {e}")
                    continue
                if result is not None:
                    extracted.append(result)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{week}.json"), "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    run()
