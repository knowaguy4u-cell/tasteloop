# TasteLoop Agent

Qloo Agentic Hackathon entry — an agentic week-planner grounded in real cultural
taste data. Describe your week + mood → get dining, music, film, and going-out
picks with tag-and-affinity-grounded explanations of *why each pick fits*,
side-by-side against a simulated generic baseline so the Qloo difference is visible.

**Status:** built and verified locally. Runs in demo-data mode until a Qloo
hackathon API key is provided (see below). Not yet deployed or submitted.

## Quickstart

```bash
python3 backend/server.py        # serves http://localhost:8000 (respects $PORT)
```

Then open http://localhost:8000. Try:
week: "Long studio week, exhausted by Friday. Want a low-key date night with
live jazz and good ramen, then a slow Sunday film." · mood: Romantic · city: Chicago

```bash
python3 -m unittest discover -s tests   # 18 tests, stdlib only
bash scripts/smoke.sh                   # boots server, hits /api/health + /api/plan
```

## Going live with Qloo

1. Request a hackathon API key via the form linked in the
   [Qloo Agentic Hackathon Developer Guide](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide)
   (Google Form, ~a few business days; check spam).
2. `export QLOO_API_KEY=<key>` and restart — the app switches to live mode
   (`GET /api/health` reports `"mode": "live"`).
3. Hackathon keys only work against `https://hackathon.api.qloo.com` — the client
   is hardcoded to it.

Without the key the app runs on a curated deterministic demo dataset, clearly
badged "DEMO DATA" in the UI. Mock data is never presented as live Qloo data.

## Deploy (free tier)

Single process, no build step, no pip deps:

```bash
# Render / Railway / Fly.io free web service
#   build:  (none)
#   start:  python3 backend/server.py        # reads $PORT
#   env:    QLOO_API_KEY=<key>
```

## Layout

```
backend/server.py            stdlib HTTP server: static frontend + /api/*
backend/providers/base.py    TasteProvider interface + card contract
backend/providers/qloo.py    real Qloo client (X-Api-Key, /v2/insights, /v2/tags, /search)
backend/providers/mock.py    deterministic demo dataset (same contract)
backend/planner.py           week text + mood → taste signals → per-category picks
backend/explainer.py         "why it fits" from real tags/affinity only
backend/baseline.py          simulated generic baseline (honestly labeled)
frontend/                    self-contained SPA (no CDNs, no build)
tests/test_backend.py        18 unittest tests (Qloo client tested with mocked HTTP)
scripts/smoke.sh             end-to-end curl smoke test
docs/ARCHITECTURE.md         design + honesty rules
SUBMISSION.md                Devpost submission draft (NOT submitted)
```

## Honesty rules (enforced in code, required by judging)

- Affinity/popularity scores pass through from the provider or are `None` — never invented.
- Explanations ground only in returned tags + matched signals.
- The generic baseline is labeled simulated everywhere it appears.

## License

MIT — see LICENSE. Built by TMTProductions1 for the Qloo Agentic Hackathon.
