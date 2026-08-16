# Reddit Signal Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the weekly Reddit signal pipeline — fetch posts, extract topics via Claude, match/amplify them into a persistent registry, and report trends — as described in the design spec.

**Architecture:** Four independent, flat Python modules (`fetch.py`, `extract.py`, `match.py`, `report.py`) chained by a `run_weekly.py` entrypoint, each also runnable standalone via `--stage`. Shared helpers (`config.py`, `credentials.py`, `state.py`, `registry.py`, `weekutil.py`) live alongside them at repo root, matching the spec's flat layout. All external calls (PRAW, Anthropic) are injected as parameters so every module is testable without live network access.

**Tech Stack:** Python 3.11+, PRAW (Reddit API), Anthropic SDK (Claude), PyYAML, `keyring`, pytest.

**Spec:** [docs/superpowers/specs/2026-08-15-reddit-signal-pipeline-design.md](../specs/2026-08-15-reddit-signal-pipeline-design.md)

## Global Constraints

- Reddit access only via the official API through PRAW — never HTML scraping.
- Never store author/username fields, or full comment trees — only the fields the spec lists: `id`, `title`, `selftext`, `permalink`, `score`, `num_comments`, `created_utc`.
- Credentials (`reddit_client_id`, `reddit_client_secret`, `reddit_user_agent`, `anthropic_api_key`) live only in the OS credential vault via `keyring`, service name `reddit-signal-pipeline` — never in a plaintext file, never committed.
- Each stage fails independently and loudly (raise/non-zero exit with a clear message) rather than silently swallowing errors, except where the spec calls out a specific skip-and-continue behavior (single post in `extract.py`).
- `fetch.py` must only persist `data/state.json` after a fully successful run over all configured subreddits, so a mid-run crash causes a safe retry rather than a skipped window.
- `match.py` / `report.py` must fail loudly on a corrupt `data/registry.json` rather than silently overwriting it.
- `match.py`'s merge/create logic and `report.py`'s trend calculations are unit tested against fixture JSON only — no live API calls in tests. `fetch.py` / `extract.py` tests use mocked PRAW / Anthropic clients.
- Packaging via `requirements.txt` (praw, anthropic, pyyaml, keyring), per the spec's stated default.
- Week identifiers are ISO week strings (`2026-W33`) computed from the run date, never user-supplied.

---

## File Structure

```
config.yaml.example       # template config (tracked); real config.yaml is gitignored
requirements.txt          # praw, anthropic, pyyaml, keyring
requirements-dev.txt      # pytest
.gitignore                # data/, config.yaml, __pycache__, .pytest_cache
conftest.py                # adds repo root to sys.path so `import fetch` etc. works from tests/
weekutil.py                # ISO week string helper
config.py                  # config.yaml loader + validation
credentials.py              # keyring wrapper (get_secret)
set_credentials.py          # one-time interactive credential setup script
state.py                    # data/state.json load/save
registry.py                  # data/registry.json load/save
fetch.py                    # Stage 1: PRAW → data/raw/<week>/<subreddit>.json
extract.py                  # Stage 2: Claude → data/extracted/<week>.json
match.py                     # Stage 3: Claude → data/registry.json (updated in place)
report.py                    # Stage 4: registry → data/reports/<week>.json/.csv
run_weekly.py                # entrypoint, chains all stages, --stage flag for single-stage runs
tests/
  test_weekutil.py
  test_config.py
  test_credentials.py
  test_set_credentials.py
  test_state.py
  test_registry.py
  test_fetch.py
  test_extract.py
  test_match.py
  test_report.py
  test_run_weekly.py
  fixtures/
    registry_sample.json
    new_topics_sample.json
```

Each module has one responsibility and no module imports another's private helpers — only their public `run()`/documented functions. `data/` is created at runtime by the modules themselves and is gitignored.

---

### Task 1: Project scaffolding + week utility

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `config.yaml.example`
- Create: `conftest.py`
- Create: `weekutil.py`
- Test: `tests/test_weekutil.py`

**Interfaces:**
- Produces: `weekutil.iso_week_string(d: datetime.date) -> str`, used by every stage module to compute the current week identifier.

- [x] **Step 1: Create scaffolding files**
- [x] **Step 2: Write the failing test for `weekutil.py`**
- [x] **Step 3: Run test to verify it fails**
- [x] **Step 4: Implement `weekutil.py`**
- [x] **Step 5: Run test to verify it passes**
- [x] **Step 6: Commit**

---

### Task 2: Config loader

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: none
- Produces: `config.py.load_config(path: str) -> dict` with keys `subreddits: list[str]`, `fetch_limit_per_subreddit: int`, `trend_window_weeks: int`. Raises `config.ConfigError` on invalid config. Used by `run_weekly.py`.

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `config.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 3: Credentials (keyring) + one-time setup script

**Files:**
- Create: `credentials.py`
- Create: `set_credentials.py`
- Test: `tests/test_credentials.py`
- Test: `tests/test_set_credentials.py`

**Interfaces:**
- Produces: `credentials.SERVICE: str`, `credentials.REQUIRED_KEYS: list[str]`, `credentials.get_secret(key: str) -> str` (raises `credentials.MissingCredentialError`). Used by `fetch.py`, `extract.py`, `match.py`.

- [x] **Step 1: Write the failing tests for `credentials.py`**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `credentials.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Write the failing test for `set_credentials.py`**
- [x] **Step 6: Run test to verify it fails**
- [x] **Step 7: Implement `set_credentials.py`**
- [x] **Step 8: Run test to verify it passes**
- [x] **Step 9: Commit**

---

### Task 4: State persistence (`data/state.json`)

**Files:**
- Create: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Produces: `state.load_state(path: str) -> dict`, `state.save_state(path: str, state: dict) -> None`. Used by `fetch.py`.

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `state.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 5: Registry persistence (`data/registry.json`)

**Files:**
- Create: `registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Produces: `registry.load_registry(path: str) -> dict` (shape `{"topics": [...]}`), `registry.save_registry(path: str, registry: dict) -> None`, `registry.RegistryError`. Used by `match.py`, `report.py`.

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `registry.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 6: `fetch.py` — Stage 1 (PRAW → raw posts + state)

**Files:**
- Create: `fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: `credentials.get_secret`, `state.load_state`/`state.save_state`, `weekutil.iso_week_string`.
- Produces: `fetch.build_reddit_client() -> praw.Reddit`, `fetch.fetch_new_posts(reddit_client, subreddit_name: str, last_seen_fullname: str | None, limit: int) -> tuple[list[dict], str]`, `fetch.run(subreddits: list[str], fetch_limit_per_subreddit: int, state_path="data/state.json", raw_dir="data/raw", today=None, reddit_client=None) -> None`. Used by `run_weekly.py`.

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `fetch.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 7: `extract.py` — Stage 2 (Claude → extracted topics)

**Files:**
- Create: `extract.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: `credentials.get_secret`, `weekutil.iso_week_string`. Reads raw post dicts written by `fetch.py` (`fetch._post_to_dict` shape: `id`, `title`, `selftext`, `permalink`, `score`, `num_comments`, `created_utc`).
- Produces: `extract.VALID_CATEGORIES: set[str]`, `extract.build_extraction_prompt(post: dict) -> str`, `extract.extract_topic(client, post: dict) -> dict | None` (raises `extract.ExtractionError`), `extract.run(raw_dir="data/raw", out_dir="data/extracted", today=None, client=None) -> None`. Extracted topic dict shape: `{"post_id", "permalink", "score", "num_comments", "topic", "description", "category"}` — consumed by `match.py`.

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `extract.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 8: `match.py` — Stage 3 (Claude → registry merge)

**Files:**
- Create: `match.py`
- Test: `tests/test_match.py`
- Create: `tests/fixtures/registry_sample.json`
- Create: `tests/fixtures/new_topics_sample.json`

**Interfaces:**
- Consumes: `registry.load_registry`/`registry.save_registry`, `credentials.get_secret`, `weekutil.iso_week_string`. Reads extracted topic dicts written by `extract.py` (shape from Task 7: `post_id`, `permalink`, `score`, `num_comments`, `topic`, `description`, `category`).
- Produces: `match.build_matching_prompt(new_topics: list[dict], existing_topics: list[dict]) -> str`, `match.apply_matches(registry: dict, new_topics: list[dict], decisions: list[dict], week: str, id_factory=...) -> dict`, `match.run(extracted_dir="data/extracted", registry_path="data/registry.json", today=None, client=None) -> None`. Consumed by `report.py` (via the registry file it writes).

- [x] **Step 1: Create fixture files**
- [x] **Step 2: Write the failing tests**
- [x] **Step 3: Run tests to verify they fail**
- [x] **Step 4: Implement `match.py`**
- [x] **Step 5: Run tests to verify they pass**
- [x] **Step 6: Commit**

---

### Task 9: `report.py` — Stage 4 (registry → trend report)

**Files:**
- Create: `report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `registry.load_registry`, `weekutil.iso_week_string`. Reads registry topic dicts as produced by `match.py` (shape: `id`, `canonical_name`, `category`, `first_seen_week`, `weekly_mentions: dict[str, int]`, `example_permalinks`).
- Produces: `report.compute_trends(registry: dict, current_week: str, trend_window_weeks: int) -> list[dict]`, `report.write_report(rows: list[dict], json_path: str, csv_path: str) -> None`, `report.run(registry_path="data/registry.json", report_dir="data/reports", trend_window_weeks=8, today=None) -> None`. Used by `run_weekly.py`.

**Design decision (not specified in the spec — documented here):** trend direction compares this week's mention count against the average of the trailing `trend_window_weeks` weeks (excluding the current week), not just the single prior week, to avoid noisy single-week swings. More than 20% above that average is `rising`, more than 20% below is `falling`, otherwise `stable`. A topic first seen this week is always `new`.

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `report.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 10: `run_weekly.py` — entrypoint with `--stage` flag

**Files:**
- Create: `run_weekly.py`
- Test: `tests/test_run_weekly.py`

**Interfaces:**
- Consumes: `config.load_config`, `fetch.run`, `extract.run`, `match.run`, `report.run` (exact signatures from Tasks 2, 6, 7, 8, 9).
- Produces: `run_weekly.STAGES: list[str]`, `run_weekly.run_all(config_path="config.yaml", today=None) -> None`, `run_weekly.main() -> None` (CLI with `--stage {fetch,extract,match,report,all}` and `--config`).

- [x] **Step 1: Write the failing tests**
- [x] **Step 2: Run tests to verify they fail**
- [x] **Step 3: Implement `run_weekly.py`**
- [x] **Step 4: Run tests to verify they pass**
- [x] **Step 5: Commit**

---

### Task 11: End-to-end integration test + setup docs

**Files:**
- Create: `tests/test_end_to_end.py`
- Modify: `README.md` (add "Setup" section)

**Interfaces:**
- Consumes: `fetch.run`, `extract.run`, `match.run`, `report.run` — exercises the full data flow from raw fetch through final report using only mocked PRAW/Anthropic clients and a `tmp_path` data directory. No new interfaces produced.

- [x] **Step 1: Write the failing integration test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Fix any integration issues found** (none needed — passed on first run)
- [x] **Step 4: Run test to verify it passes**
- [x] **Step 5: Run the full test suite** (44 passed)
- [x] **Step 6: Add setup instructions to README.md**
- [x] **Step 7: Commit**

---

## Self-Review

**Spec coverage:**
- Four pipeline stages (fetch/extract/match/report) chained by `run_weekly.py` — Tasks 6-10. ✓
- `config.yaml` with `subreddits`, `fetch_limit_per_subreddit`, `trend_window_weeks` — Task 2. ✓
- Minimal field retention, no author/username, skip deleted/removed — Task 6. ✓
- State updated only after full success — Task 6 (`test_run_leaves_state_untouched_when_a_subreddit_fetch_fails`). ✓
- Claude extraction with category enum and skip-on-error — Task 7. ✓
- Registry matching/merge with mention counts and permalinks — Task 8. ✓
- Trend report (new/rising/stable/falling) as JSON + CSV — Task 9. ✓
- Credentials via `keyring`, one-time `set_credentials.py`, never on disk — Task 3. ✓
- Registry/state corruption fails loudly rather than silently overwriting — Task 5 (`RegistryError`). ✓
- Fixture-based, no-live-API testing for match/report; mocked-client testing for fetch/extract — Tasks 6-9 throughout. ✓
- CLI single-stage execution — Task 10. ✓
- `requirements.txt` packaging default — Task 1. ✓
- End-to-end data flow and setup docs — Task 11. ✓

**Execution outcome:** All 11 tasks implemented via strict TDD (failing test → implementation → passing test → commit). Full suite: 44 tests passed. The end-to-end integration test (Task 11) passed on the first run with no wiring fixes needed — the interface contracts documented per-task held exactly as specified.
