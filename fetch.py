import json
import os
from datetime import date

import praw
import prawcore

from credentials import get_secret
from state import load_state, save_state
from weekutil import iso_week_string

REMOVED_MARKERS = {"[deleted]", "[removed]"}


class FetchError(Exception):
    pass


def _wrap_prawcore_error(subreddit_name: str, error: prawcore.exceptions.PrawcoreException) -> FetchError:
    if isinstance(error, prawcore.exceptions.RequestException):
        return FetchError(
            f"r/{subreddit_name}: Reddit API unavailable (network error): {error.original_exception}"
        )
    if isinstance(error, prawcore.exceptions.TooManyRequests):
        return FetchError(f"r/{subreddit_name}: Reddit API rate-limited: {error}")
    if isinstance(error, (prawcore.exceptions.OAuthException, prawcore.exceptions.Forbidden)):
        return FetchError(f"r/{subreddit_name}: Reddit API authentication/authorization error: {error}")
    if isinstance(error, prawcore.exceptions.ServerError):
        return FetchError(f"r/{subreddit_name}: Reddit API server error (5xx): {error}")
    return FetchError(f"r/{subreddit_name}: Reddit API error: {error}")


def build_reddit_client():
    return praw.Reddit(
        client_id=get_secret("reddit_client_id"),
        client_secret=get_secret("reddit_client_secret"),
        user_agent=get_secret("reddit_user_agent"),
    )


def _is_removed(submission) -> bool:
    return submission.title in REMOVED_MARKERS or submission.selftext in REMOVED_MARKERS


def _post_to_dict(submission) -> dict:
    return {
        "id": submission.id,
        "title": submission.title,
        "selftext": submission.selftext,
        "permalink": submission.permalink,
        "score": submission.score,
        "num_comments": submission.num_comments,
        "created_utc": submission.created_utc,
    }


def fetch_new_posts(reddit_client, subreddit_name, last_seen_fullname, limit):
    subreddit = reddit_client.subreddit(subreddit_name)
    posts = []
    newest_fullname = last_seen_fullname

    try:
        for submission in subreddit.new(limit=limit):
            if newest_fullname == last_seen_fullname:
                newest_fullname = submission.fullname

            if submission.fullname == last_seen_fullname:
                break

            if _is_removed(submission):
                continue

            posts.append(_post_to_dict(submission))
    except prawcore.exceptions.PrawcoreException as e:
        raise _wrap_prawcore_error(subreddit_name, e) from e

    return posts, newest_fullname


def run(subreddits, fetch_limit_per_subreddit, state_path="data/state.json", raw_dir="data/raw", today=None, reddit_client=None):
    reddit_client = reddit_client or build_reddit_client()
    state = load_state(state_path)
    week = iso_week_string(today or date.today())
    week_dir = os.path.join(raw_dir, week)
    os.makedirs(week_dir, exist_ok=True)

    for subreddit_name in subreddits:
        last_seen = state.get(subreddit_name)
        posts, newest = fetch_new_posts(reddit_client, subreddit_name, last_seen, fetch_limit_per_subreddit)

        out_path = os.path.join(week_dir, f"{subreddit_name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2, sort_keys=True)

        state[subreddit_name] = newest

    save_state(state_path, state)


if __name__ == "__main__":
    run(subreddits=[], fetch_limit_per_subreddit=100)
