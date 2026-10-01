"""Week planner: free-text week context + mood + city -> taste signals -> picks.

Signal extraction is a documented heuristic: a curated KEYWORD -> tag-name
map plus per-mood tag seeds. It is keyword matching, not NLP — the docstring
on KEYWORD_MAP says so, and plan_week returns the matched keywords and tag
names so the UI can show exactly what was detected.
"""

import re

# ---------------------------------------------------------------------------
# Heuristic keyword -> tag-name map (~80 entries). Matching is case-insensitive
# substring-on-word-boundaries over the user's week text. Tags are plain names;
# the provider layer resolves them to API tag URNs (Qloo) or matches them
# against curated data (mock).
# ---------------------------------------------------------------------------
KEYWORD_MAP = {
    # food & drink
    "sushi": ["sushi", "japanese"],
    "ramen": ["ramen", "japanese", "noodles"],
    "tacos": ["tacos", "mexican", "street food"],
    "burrito": ["mexican", "casual"],
    "pizza": ["pizza", "italian"],
    "pasta": ["pasta", "italian"],
    "italian": ["italian"],
    "thai": ["thai", "asian"],
    "indian": ["indian", "curry"],
    "curry": ["curry", "indian"],
    "dim sum": ["dim sum", "chinese"],
    "pho": ["vietnamese", "noodles"],
    "barbecue": ["barbecue", "bbq"],
    "bbq": ["barbecue", "bbq"],
    "burger": ["burgers", "american"],
    "steak": ["steakhouse", "steak"],
    "seafood": ["seafood"],
    "brunch": ["brunch", "cafe"],
    "vegan": ["vegan", "plant-based"],
    "coffee": ["coffee", "cafe"],
    "wine": ["wine", "wine bar"],
    "cocktail": ["cocktails", "speakeasy"],
    "craft beer": ["craft beer", "brewery"],
    "brewery": ["brewery", "craft beer"],
    "whiskey": ["whiskey", "cocktails"],
    "food truck": ["food truck", "street food"],
    "farmers market": ["farmers market", "local food"],
    "rooftop": ["rooftop", "cocktails"],
    # music
    "jazz": ["jazz", "live music"],
    "blues": ["blues", "live music"],
    "soul": ["soul", "r&b"],
    "r&b": ["r&b", "soul"],
    "hip-hop": ["hip-hop"],
    "hip hop": ["hip-hop"],
    "electronic": ["electronic", "edm"],
    "edm": ["edm", "electronic"],
    "techno": ["techno", "electronic", "club"],
    "house music": ["house", "electronic", "dance"],
    "disco": ["disco", "dance", "funk"],
    "funk": ["funk", "soul"],
    "rock": ["rock"],
    "indie": ["indie", "indie rock", "independent film"],
    "punk": ["punk", "rock"],
    "metal": ["metal"],
    "folk": ["folk", "acoustic"],
    "country": ["country"],
    "classical": ["classical", "orchestral"],
    "opera": ["opera", "classical"],
    "pop": ["pop"],
    "k-pop": ["k-pop", "pop"],
    "latin": ["latin", "reggaeton"],
    "reggaeton": ["reggaeton", "latin"],
    "motown": ["motown", "soul"],
    "gospel": ["gospel", "soul"],
    "lo-fi": ["lo-fi", "chill"],
    "ambient": ["ambient", "chill"],
    "vinyl": ["vinyl", "record store"],
    "live music": ["live music", "concert"],
    "concert": ["concert", "live music"],
    "karaoke": ["karaoke", "nightlife"],
    # film & tv
    "horror": ["horror", "thriller"],
    "thriller": ["thriller"],
    "sci-fi": ["sci-fi", "science fiction"],
    "documentary": ["documentary"],
    "anime": ["anime", "animation"],
    "animation": ["animation", "anime"],
    "rom-com": ["romance", "comedy"],
    "romance": ["romance", "romantic"],
    "cult classic": ["cult classic"],
    "drive-in": ["drive-in", "movie"],
    "film festival": ["film festival", "independent film"],
    # going out / activities
    "hiking": ["hiking", "outdoors", "nature"],
    "camping": ["camping", "outdoors"],
    "picnic": ["picnic", "outdoors"],
    "mini golf": ["mini golf", "outdoors"],
    "club": ["club", "nightlife", "dance"],
    "dance": ["dance", "dancing", "club"],
    "speakeasy": ["speakeasy", "cocktails"],
    "comedy": ["comedy", "stand-up"],
    "stand-up": ["stand-up", "comedy"],
    "improv": ["improv", "comedy"],
    "trivia": ["trivia", "bar"],
    "arcade": ["arcade", "retro gaming"],
    "bowling": ["bowling", "retro"],
    "board games": ["board games", "cafe"],
    "escape room": ["escape room", "adventure"],
    "museum": ["museum", "art"],
    "art": ["art", "gallery"],
    "gallery": ["gallery", "art"],
    "theater": ["theater", "performing arts"],
    "ballet": ["ballet", "performing arts"],
    "yoga": ["yoga", "wellness"],
    "spa": ["spa", "wellness"],
    "books": ["books", "bookstore"],
    "reading": ["books", "bookstore"],
    "stargazing": ["stargazing", "outdoors"],
}

MOOD_TAGS = {
    "chill": ["chill", "acoustic", "ambient", "lo-fi", "cozy", "slow food"],
    "energetic": ["energetic", "upbeat", "dance", "edm", "nightlife", "street food"],
    "romantic": ["romantic", "candlelit", "wine", "soul", "jazz", "intimate"],
    "adventurous": ["adventurous", "experimental", "street food", "craft beer", "indie rock", "hiking"],
    "focused": ["focused", "instrumental", "classical", "coffee", "minimal", "ambient"],
    "nostalgic": ["nostalgic", "retro", "classic rock", "vintage", "diner", "cult classic"],
}

CATEGORIES = ("dining", "music", "film", "going_out")


def extract_signals(week_text, mood):
    """Return (keywords, tag_names): matched keywords and ordered unique tag names."""
    text = (week_text or "").lower()
    keywords = []
    tag_names = []
    for keyword, tags in KEYWORD_MAP.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text):
            keywords.append(keyword)
            tag_names.extend(tags)
    mood_key = (mood or "").strip().lower()
    tag_names.extend(MOOD_TAGS.get(mood_key, []))
    # de-dupe, preserve order
    seen = set()
    unique_tags = [t for t in tag_names if not (t in seen or seen.add(t))]
    return keywords, unique_tags


def plan_week(week_text, mood, city, provider, take=6):
    """Build the week's taste-matched plan.

    Returns {"signals": {"mood", "tag_names", "keywords"},
             "picks": {"dining": [...], "music": [...], "film": [...], "going_out": [...]}}.
    Affinity/popularity values are passed through from the provider untouched.
    """
    keywords, tag_names = extract_signals(week_text, mood)
    picks = {}
    for category in CATEGORIES:
        picks[category] = provider.recommend(
            category, tag_names, city or "", take=take
        )
    return {
        "signals": {
            "mood": (mood or "").strip().lower(),
            "tag_names": tag_names,
            "keywords": keywords,
        },
        "picks": picks,
    }
