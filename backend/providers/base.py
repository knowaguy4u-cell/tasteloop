"""TasteProvider interface for the TasteLoop Agent backend.

A "card" is the normalized recommendation unit used everywhere in the app:

    {
        "name": str,            # entity / venue / artist / film name
        "category": str,        # one of: dining, music, film, going_out
        "affinity": float|None, # 0-1 taste affinity from the provider (never invented)
        "popularity": float|None,# 0-1 popularity from the provider (never invented)
        "tags": [str],          # tag names describing the entity
        "image": str|None,      # image URL, if the provider supplies one
        "source": str,          # "qloo" | "mock" | "baseline"
    }

Implementations must never invent affinity/popularity numbers: pass through
whatever the provider returns, or None when the provider has no value.
"""

CATEGORIES = ("dining", "music", "film", "going_out")


class TasteProvider:
    """Interface every taste provider must implement."""

    def recommend(self, category, tag_names, location, take=6):
        """Return up to `take` cards for `category` matching `tag_names`.

        category: one of CATEGORIES. tag_names: list of tag-name strings.
        location: city string (may be "" or None). take: 1..50.
        Returns: list of card dicts (see module docstring).
        """
        raise NotImplementedError

    def search_entity(self, query, etype=None):
        """Search entities by keyword; returns list of card-ish dicts."""
        raise NotImplementedError

    def search_tags(self, query, take=10):
        """Search tags by keyword; returns list of {"id", "name"} dicts."""
        raise NotImplementedError


def validate_card(card):
    """Return True if `card` satisfies the card contract, False otherwise."""
    if not isinstance(card, dict):
        return False
    required = ("name", "category", "affinity", "popularity", "tags", "image", "source")
    if any(k not in card for k in required):
        return False
    if not isinstance(card["name"], str) or not card["name"]:
        return False
    if card["category"] not in CATEGORIES:
        return False
    for key in ("affinity", "popularity"):
        v = card[key]
        if v is not None and not (isinstance(v, (int, float)) and 0.0 <= v <= 1.0):
            return False
    if not isinstance(card["tags"], list) or not all(isinstance(t, str) for t in card["tags"]):
        return False
    if card["image"] is not None and not isinstance(card["image"], str):
        return False
    if not isinstance(card["source"], str) or not card["source"]:
        return False
    return True
