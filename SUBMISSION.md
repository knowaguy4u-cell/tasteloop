# Devpost submission draft — TasteLoop Agent (DO NOT SUBMIT — Tim's tap required)

**Hackathon:** Qloo Agentic Hackathon (https://qloo.devpost.com/)
**Team/display name:** TMTProductions1
**Demo URL:** [TO FILL — externally hosted app URL after deploy]
**Repo URL:** [TO FILL — public GitHub repo URL after push]
**Video:** not required for this hackathon — none.

---

**Tagline:** Your week, planned by taste — an agent that turns "I'm exhausted and
want jazz and ramen Friday" into a culturally-grounded plan, and shows its work.

**Description:**

TasteLoop Agent takes a user's week — free-text context plus a mood — and returns
a plan across dining, music, film, and going out. Every pick ships with a
plain-language explanation of *why it fits*, built from real taste data rather
than vibes.

**What's Qloo-powered:** the agent resolves the user's words to Qloo taste tags
(via `/v2/tags`), then queries the Insights API (`/v2/insights`) with
`signal.interests.tags` across four entity types — `urn:entity:place` (dining),
`urn:entity:artist` (music), `urn:entity:movie` (film), `urn:entity:place`
(venues). Each recommendation carries Qloo's affinity score (0–1 against the
user's taste signals), popularity weighting, and taxonomy tags — and the "why it
fits" copy is generated exclusively from that returned metadata. No invented
scores, no generic filler.

**The differentiator judges asked for:** the app renders a side-by-side toggle —
Qloo-grounded picks vs. a simulated generic baseline ("Top-rated chain
restaurant near you"). Same input, visibly different specificity. The contrast
*is* the demo: cultural grounding beats generic-LLM-style guessing, and you can
see exactly which taste signals drove each pick.

**How it's built:** one Python process (stdlib only — zero dependencies) serves
a self-contained single-page app and a `/api/plan` endpoint. A provider
interface swaps between the live Qloo client and a deterministic demo dataset,
so the app degrades gracefully and never presents mock data as live. Deploys to
any free-tier host with `python3 backend/server.py`.

**What's next:** user taste profiles that persist across weeks (Qloo audience
signals), calendar import for real schedule context, and city-aware venue
ranking via Qloo location filters.
