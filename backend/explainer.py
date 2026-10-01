"""Explainer: template-based "why it fits" grounded ONLY in real card data.

Rules enforced here:
- Mention only tags actually present on the card, and only signal tags that
  genuinely match a card tag.
- Mention affinity/popularity only when the card carries a non-None value.
- Never claim awards, reviews, critic scores, or anything not in the card.
- Output is always 1-2 sentences.
"""


def _match(card_tags, signal_tags):
    """Signal tags that genuinely overlap a card tag (case-insensitive, either direction)."""
    matched = []
    lowered = [(t or "").lower() for t in card_tags]
    for sig in signal_tags or []:
        sl = (sig or "").strip().lower()
        if not sl:
            continue
        if any(sl == t or sl in t or t in sl for t in lowered) and sl not in matched:
            matched.append(sl)
    return matched


def explain(card, signals, mood):
    """Return a 1-2 sentence why-it-fits string for `card`.

    card: card dict (name, tags, affinity, popularity, ...).
    signals: {"tag_names": [...], ...}. mood: mood string.
    """
    name = card.get("name") or "This pick"
    card_tags = card.get("tags") or []
    tag_names = (signals or {}).get("tag_names") or []
    mood = (mood or "").strip().lower() or "your"

    matched = _match(card_tags, tag_names)

    shown_tags = ", ".join(card_tags[:3]) if card_tags else "its vibe"
    if matched:
        first = (
            "%s fits the %s mood \u2014 tagged %s, which lines up with your "
            "signals for %s."
            % (name, mood, shown_tags, ", ".join(matched[:3]))
        )
    else:
        first = "%s fits the %s mood \u2014 tagged %s." % (name, mood, shown_tags)

    affinity = card.get("affinity")
    popularity = card.get("popularity")
    second_bits = []
    if affinity is not None:
        second_bits.append("taste affinity %.0f%%" % (affinity * 100))
    if popularity is not None:
        second_bits.append("popularity %.0f%%" % (popularity * 100))
    if second_bits:
        second = "Scores: %s." % ", ".join(second_bits)
        return first + " " + second
    return first
