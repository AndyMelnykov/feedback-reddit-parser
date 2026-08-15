# Reddit Signal Pipeline — Design

## Purpose

Track a small set of niche, product-specific subreddits on a weekly cadence to surface
what users are asking for, complaining about, or excited about — as an input signal for
product prioritization. Must use the official Reddit API (not HTML scraping) so the
approach is fully compliant with Reddit's API Terms of Use.

## Non-goals

- Not a real-time monitoring system — weekly batch is the target cadence.
- Not a dashboard/UI — output is structured data (JSON/CSV) for the user to consume or
  feed into their own tooling.
- Not a general-purpose Reddit crawler — scoped to a configured list of subreddits.

## Architecture

Four independent, file-based pipeline stages, chained by a single entrypoint. Each stage
is a plain Python module that can also be run standalone (useful for re-running a step
without re-hitting external APIs).

```
run_weekly.py
  └─> fetch.py    → data/raw/<week>/<subreddit>.json
  └─> extract.py  → data/extracted/<week>.json
  └─> match.py    → data/registry.json (updated in place)
  └─> report.py   → data/reports/<week>.json, data/reports/<week>.csv
```

### fetch.py

- Uses PRAW (official Reddit API wrapper) with a Reddit "script"-type OAuth app.
- For each subreddit in `config.yaml`, fetches new posts newer than the last-seen post
  recorded in `data/state.json`.
- Stores minimal fields only: `id`, `title`, `selftext`, `permalink`, `score`,
  `num_comments`, `created_utc`. No author/username — not needed for topic-trend
  analysis, and avoids storing unnecessary personal data.
- Skips posts marked `[deleted]`/`[removed]`.
- Updates `data/state.json` with the newest fullname seen per subreddit — but only after
  a successful run, so a crash mid-fetch causes the next run to safely retry the same
  window rather than skipping posts.

### extract.py

- For each new post, calls the Claude API (Anthropic SDK) to extract:
  - a short topic name
  - a one-line description
  - a category: `feature_request` / `complaint` / `praise` / `question` /
    `competitor_comparison`
- One bad post (API error, malformed response) is logged and skipped — it does not abort
  the batch.
- Writes results to `data/extracted/<week>.json`.

### match.py

- Loads the persistent `data/registry.json` — the all-time list of canonical topics with
  per-week mention counts.
- Batches the new topics + the existing canonical topic list into a single Claude prompt
  per run, asking it to match each new topic to an existing canonical topic (if
  semantically the same) or flag it as new.
- On match: increments that topic's mention count for the current week, appends an
  example permalink.
- On no match: creates a new canonical topic entry.
- Updates `data/registry.json` in place.

### report.py

- Reads `data/registry.json`, computes for the current week:
  - top topics by raw mention count
  - top topics by week-over-week growth (new / rising / stable / falling)
- Writes `data/reports/<week>.json` and an equivalent `.csv`.
- Purely derived from the registry — no separate state to maintain.

## Data formats

**`config.yaml`** — user-editable tunables:
```yaml
subreddits:
  - yourproductname
  - relatedcommunity
fetch_limit_per_subreddit: 100
trend_window_weeks: 8  # how many past weeks report.py considers for trend direction
```
(Topic matching is judged by Claude, not a tunable numeric threshold, so there's no
similarity setting to configure.)

**Credentials — OS credential store, not a file.** A one-time `set_credentials.py` script
prompts for each secret and saves it into the OS's native credential vault via the
`keyring` library (Windows Credential Manager / macOS Keychain / Linux Secret Service).
The pipeline reads them back at runtime with `keyring.get_password(...)`. No secret is
ever written to a file on disk, so there's nothing to gitignore-forget or accidentally
commit.

```python
# set_credentials.py (run once, interactively)
import keyring, getpass

SERVICE = "reddit-signal-pipeline"
for key in ["reddit_client_id", "reddit_client_secret", "reddit_user_agent", "anthropic_api_key"]:
    keyring.set_password(SERVICE, key, getpass.getpass(f"{key}: "))
```

```python
# used by fetch.py / extract.py at runtime
import keyring
SERVICE = "reddit-signal-pipeline"
client_id = keyring.get_password(SERVICE, "reddit_client_id")
```

Caveat: the weekly scheduled task must run under your own Windows user account (not
`SYSTEM` or a different account) — Credential Manager entries are keyed to the account
that created them.

**`data/state.json`**:
```json
{ "yourproductname": "t3_abc123", "relatedcommunity": "t3_def456" }
```

**`data/registry.json`**:
```json
{
  "topics": [
    {
      "id": "t_001",
      "canonical_name": "Dark mode support",
      "description": "Users requesting a dark theme option",
      "category": "feature_request",
      "first_seen_week": "2026-W30",
      "weekly_mentions": { "2026-W30": 2, "2026-W33": 5 },
      "example_permalinks": ["https://reddit.com/r/.../comments/..."]
    }
  ]
}
```

Week identifiers are ISO week strings (`2026-W33`), computed from the run date — not
user-supplied.

## Reddit API compliance

- OAuth via a Reddit "script"-type app (client ID + secret from reddit.com/prefs/apps),
  accessed through PRAW — the sanctioned API path, not HTML scraping.
- User-Agent set to Reddit's required format:
  `platform:app-id:version (by /u/your-username)`.
- Rate limiting handled automatically by PRAW's built-in throttling to Reddit's published
  limits — no custom throttling needed at this volume/cadence.
- Only configured public subreddits are accessed; no private/quarantined content.
- Minimal data retention: no author/username fields stored, no full comment trees beyond
  what's needed for topic context.
- Credentials (Reddit client ID/secret, Anthropic API key) live only in the OS credential
  vault via `keyring` — never in a plaintext file, never committed to the repo.

## Error handling

- Each stage fails independently and loudly (non-zero exit, clear log message).
- `fetch.py`: on failure, `state.json` is left untouched so the next run retries the same
  window instead of silently skipping posts.
- `extract.py`: a single post's extraction failure is logged and skipped; the rest of the
  batch proceeds.
- `match.py` / `report.py`: fail loudly on a corrupt registry rather than silently
  overwriting it — the registry is the one piece of state that accumulates value over
  time and must not be casually clobbered.

## Testing

- `match.py`'s merge/create logic and `report.py`'s trend calculations are unit tested
  against fixture JSON (registry + new-topics inputs) — no live API calls.
- `fetch.py` / `extract.py` get lightly tested with mocked PRAW / Anthropic clients to
  verify field mapping and skip-on-error behavior.

## Open items for implementation planning

- Exact Claude prompt templates for extraction and matching.
- CLI argument handling for running a single stage manually (e.g. re-running `match.py`
  after fixing a bug, without re-fetching).
- Packaging: `requirements.txt` (praw, anthropic, pyyaml, keyring) vs. a lockfile tool —
  default to `requirements.txt` for simplicity unless the user prefers otherwise.
