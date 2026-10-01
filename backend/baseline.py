"""Simulated generic baseline: obviously-generic picks for side-by-side comparison.

Honestly generic by design — every card carries source="baseline",
affinity=None, and the same disclaimer as its "why". Used to show what a
non-personalized recommender would return next to TasteLoop's taste-matched
picks.
"""

BASELINE_WHY = "Popular overall \u2014 not matched to your taste signals."

_GENERIC = {
    "dining": [
        "Top-rated chain restaurant near you",
        "Most-reviewed spot downtown",
        "Trending brunch place on social media",
    ],
    "music": [
        "Today's Top 40 playlist",
        "Viral hits compilation",
        "Most-streamed artist this week",
    ],
    "film": [
        "This week's #1 box-office hit",
        "Top-trending streaming series",
        "Most-watched movie trailer",
    ],
    "going_out": [
        "Popular downtown bar",
        "Highest-rated club in the city",
        "Trending rooftop lounge",
    ],
}


def baseline_plan():
    """Return {category: [card, ...]} of generic picks, each with its disclaimer "why"."""
    plan = {}
    for category, names in _GENERIC.items():
        plan[category] = [
            {
                "name": name,
                "category": category,
                "affinity": None,
                "popularity": None,
                "tags": ["popular", "generic"],
                "image": None,
                "source": "baseline",
                "why": BASELINE_WHY,
            }
            for name in names
        ]
    return plan
