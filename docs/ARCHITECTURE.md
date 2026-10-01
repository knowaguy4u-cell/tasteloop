# TasteLoop Agent — Architecture

Qloo Agentic Hackathon entry (deadline Oct 30, 2026 10:45 PM CDT). Single deployable unit:
one Python process serves the SPA frontend and the planner API. Stdlib only — no pip deps.

## Request flow

```
browser → index.html / app.js (static)
        → POST /api/plan {week_text, mood, city}
            → planner.plan_week()
                → keyword→tag signal extraction (planner.KEYWORD_TAGS, heuristic, documented)
                → provider.recommend(category, tag_names, city) × 4 categories
                → explainer.explain(card, signals) → "why it fits" per card
                → baseline picks (simulated generic, honestly labeled)
            → {plan, baseline, signals, mode}
```

## Provider abstraction (backend/providers/)

`TasteProvider` interface — `recommend()`, `search_entity()`, `search_tags()`.
Card shape: `{name, category, affinity|None, popularity|None, tags[], image|None, source}`.

- `qloo.py` — real client. Base `https://hackathon.api.qloo.com`, `X-Api-Key` header,
  `GET /v2/insights?filter.type=…&signal.interests.tags=…&take=…`. Tag names resolved
  to URNs via `GET /v2/tags` (in-memory cache). Active when `QLOO_API_KEY` is set.
- `mock.py` — deterministic curated dataset, same card shape, `source="mock"`.
  Powers local dev + the demo until the key arrives. Clearly labeled in the UI.

Category → Qloo `filter.type`: dining → `urn:entity:place`, music → `urn:entity:artist`,
film → `urn:entity:movie`, going_out → `urn:entity:place` (venue-flavored tags).

## The "Qloo grounding" diff (judging criterion)

The app renders two views from one input:
1. **Qloo-grounded** — picks carry `affinity` (0–1 vs the user's taste signals),
   Qloo taxonomy tags, and a `why` generated *only* from returned metadata.
2. **Generic baseline** — simulated popular-overall picks, `affinity=None`,
   labeled "matched to nothing."

Same input, visibly different specificity. That contrast is the demo's argument.

## Failure behavior

- No key → mock mode, badge says DEMO DATA. Never implies mock data is live.
- Key set but Qloo errors → fall back to mock, include `warning` in response. Never 500s.
- Invalid Qloo params are silently ignored by the API — `qloo.py` only sends
  documented params (filter.type, signal.interests.tags, take, filter.location.query).

## Deploy

Single process: `python3 backend/server.py` (respects `$PORT`, default 8000).
Free-tier target: Render/Railway/Fly web service. No build step; no secrets in the repo
(key via env var only).

## Honesty rules (enforced in code)

- Affinity/popularity are passed through, never invented (None when absent).
- `explainer.py` grounds "why" text only in card metadata + matched signals.
- Baseline is labeled simulated in UI copy and API (`source="baseline"`).
