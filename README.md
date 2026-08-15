# feedback-reddit-parser

Automatically surface what people are saying about your product on Reddit — without
having to read every thread yourself.

## The problem

Customers and potential customers talk about your product on Reddit, but that feedback
is scattered across subreddits, buried in comment threads, and easy to miss. Manually
reading every thread doesn't scale, and a lot of what's there is noise: AI-generated
replies, off-topic chatter, low-effort comments that don't say anything useful.

## What this does

A weekly pipeline that:

1. **Collects** — pulls new posts from a configured list of subreddits via the official
   Reddit API.
2. **Extracts signal** — uses Claude to pull out the actual topic from each post
   (feature request, complaint, praise, question, competitor comparison), filtering out
   AI slop and irrelevant noise.
3. **Amplifies** — matches new topics against a running registry of canonical topics, so
   a subject that keeps coming back across threads, gets more comments, or attracts more
   upvotes shows up as a stronger, growing signal rather than a one-off mention.
4. **Reports** — turns the registry into a ranked view of what's trending, rising, or
   fading, as structured JSON/CSV you can feed into your own tools.

The result is an ongoing, low-effort read on what your product's community actually cares
about, instead of anecdotal impressions from whichever thread you happened to see.

## Status

Design phase — see
[docs/superpowers/specs/2026-08-15-reddit-signal-pipeline-design.md](docs/superpowers/specs/2026-08-15-reddit-signal-pipeline-design.md)
for the full architecture, data formats, and Reddit API compliance approach. No
implementation yet.

## Architecture (planned)

Four independent, file-based stages chained by a single entrypoint. Each stage is a
plain Python module and can also be run standalone.

```text
run_weekly.py
  └─> fetch.py    → data/raw/<week>/<subreddit>.json
  └─> extract.py  → data/extracted/<week>.json
  └─> match.py    → data/registry.json (updated in place)
  └─> report.py   → data/reports/<week>.json, data/reports/<week>.csv
```

- **fetch.py** — pulls new posts per subreddit via PRAW (official Reddit API wrapper),
  storing only the minimal fields needed for topic analysis.
- **extract.py** — calls the Claude API per post to extract a topic, description, and
  category.
- **match.py** — merges new topics into the persistent registry, matching against
  existing canonical topics or creating new ones.
- **report.py** — computes top topics by mention count and week-over-week trend
  (new / rising / stable / falling) from the registry.

Credentials (Reddit API + Anthropic API keys) are stored in the OS credential vault via
`keyring` — never in a plaintext file, never committed to the repo.

## Reddit API compliance

Built on the official Reddit API (via PRAW), not HTML scraping — only configured public
subreddits, minimal data retention (no author/username stored), and rate limiting
handled by PRAW's built-in throttling. See the design spec for details.

## License

See [LICENSE](LICENSE).
