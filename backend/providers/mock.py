"""MockProvider: deterministic curated dataset powering the demo until QLOO_API_KEY arrives.

Satisfies the same card contract as QlooProvider (see base.py). recommend()
scores entities by tag-name overlap with the requested tags (exact
case-insensitive token match, plus substring containment), then by affinity —
fully deterministic, no randomness, no invented numbers beyond the curated
affinity/popularity values below.
"""

from .base import TasteProvider

# (name, tags, affinity, popularity)
_DATA = {
    "dining": [
        ("Ember & Oak", ["wood-fired", "seasonal", "farm-to-table", "cozy"], 0.91, 0.78),
        ("Midnight Ramen Bar", ["ramen", "japanese", "late-night", "noodles"], 0.88, 0.82),
        ("Casa Verde Taqueria", ["tacos", "mexican", "street food", "casual"], 0.84, 0.71),
        ("The Copper Still", ["steakhouse", "whiskey", "cocktails", "date night"], 0.93, 0.69),
        ("Juniper Wine Garden", ["wine", "wine bar", "garden", "romantic"], 0.89, 0.74),
        ("Golden Hour Brunch Club", ["brunch", "cafe", "weekend", "pancakes"], 0.81, 0.86),
        ("Sable & Smoke BBQ", ["barbecue", "bbq", "smokehouse", "craft beer"], 0.77, 0.73),
    ],
    "music": [
        ("The Velvet Static", ["indie rock", "live music", "guitar"], 0.90, 0.62),
        ("DJ Marisol Vega", ["house", "electronic", "dance", "club"], 0.87, 0.58),
        ("Blue Note Quartet", ["jazz", "live music", "intimate"], 0.94, 0.55),
        ("Cassette Hearts", ["synth-pop", "retro", "dance"], 0.83, 0.66),
        ("The Hollis Brothers", ["folk", "acoustic", "harmonies"], 0.79, 0.49),
        ("Nova Rae", ["r&b", "soul", "smooth"], 0.92, 0.71),
        ("Iron Meridian", ["metal", "heavy", "live music"], 0.74, 0.52),
    ],
    "film": [
        ("The Last Projectionist", ["independent film", "drama", "nostalgic"], 0.90, 0.61),
        ("Neon Requiem", ["sci-fi", "neo-noir", "thriller"], 0.86, 0.68),
        ("Salt & Cinder", ["documentary", "food", "culture"], 0.82, 0.57),
        ("Midnight at the Roxy", ["horror", "midnight movie", "cult classic"], 0.78, 0.64),
        ("Paper Moons", ["romance", "romantic", "drama"], 0.88, 0.59),
        ("The Cartographer's Daughter", ["adventure", "fantasy", "epic"], 0.84, 0.72),
        ("Static Bloom", ["animation", "anime", "coming-of-age"], 0.81, 0.63),
    ],
    "going_out": [
        ("The Alchemist's Den", ["speakeasy", "cocktails", "intimate"], 0.93, 0.70),
        ("Rooftop Meridian", ["rooftop", "cocktails", "skyline", "dance"], 0.89, 0.80),
        ("Velvet Circuit", ["club", "electronic", "late-night", "dance"], 0.85, 0.75),
        ("Laugh Track Comedy Loft", ["comedy", "stand-up", "improv"], 0.80, 0.60),
        ("The Analog Arcade", ["arcade", "retro gaming", "bar"], 0.76, 0.67),
        ("Harbor Lights Jazz Cellar", ["jazz", "live music", "cocktails", "intimate"], 0.95, 0.58),
        ("Stargazer Observatory Nights", ["stargazing", "outdoors", "unique"], 0.82, 0.45),
    ],
}


def _overlap_score(entity_tags, wanted):
    """Count wanted tags that match an entity tag (case-insensitive, either direction)."""
    score = 0
    lowered = [t.lower() for t in entity_tags]
    for w in wanted:
        wl = w.strip().lower()
        if not wl:
            continue
        if any(wl == t or wl in t or t in wl for t in lowered):
            score += 1
    return score


def _make_card(name, category, tags, affinity, popularity):
    return {
        "name": name,
        "category": category,
        "affinity": affinity,
        "popularity": popularity,
        "tags": list(tags),
        "image": None,
        "source": "mock",
    }


class MockProvider(TasteProvider):
    """Deterministic curated provider. No network, no key, no randomness."""

    def recommend(self, category, tag_names, location, take=6):
        if category not in _DATA:
            raise ValueError("unknown category: %r" % (category,))
        tag_names = list(tag_names or [])
        take = max(1, min(int(take or 6), 50))
        scored = []
        for name, tags, affinity, popularity in _DATA[category]:
            score = _overlap_score(tags, tag_names)
            scored.append((-score, -affinity, name,
                           _make_card(name, category, tags, affinity, popularity)))
        scored.sort()
        return [card for _, _, _, card in scored[:take]]

    def search_entity(self, query, etype=None):
        q = (query or "").strip().lower()
        out = []
        for category, rows in _DATA.items():
            for name, tags, affinity, popularity in rows:
                if not q or q in name.lower():
                    out.append(_make_card(name, category, tags, affinity, popularity))
        return out

    def search_tags(self, query, take=10):
        q = (query or "").strip().lower()
        seen = {}
        for rows in _DATA.values():
            for _, tags, _, _ in rows:
                for t in tags:
                    if (not q or q in t.lower()) and t.lower() not in seen:
                        seen[t.lower()] = {"id": "mock:tag:" + t.lower().replace(" ", "_"),
                                           "name": t}
        return list(seen.values())[: max(1, int(take or 10))]
