"""TasteLoop backend test suite (stdlib unittest only)."""

import io
import json
import os
import sys
import unittest
import urllib.request
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.baseline import BASELINE_WHY, baseline_plan
from backend.explainer import explain
from backend.planner import extract_signals, plan_week
from backend.providers.base import CATEGORIES, validate_card
from backend.providers.mock import MockProvider
from backend.providers.qloo import (
    CATEGORY_FILTER_TYPES,
    QlooError,
    QlooNotConfigured,
    QlooProvider,
)


# ---------------------------------------------------------------- planner
class TestPlannerSignals(unittest.TestCase):
    def test_known_keywords_map_to_tags(self):
        keywords, tags = extract_signals(
            "Friday night: jazz club, then sushi with friends", "chill"
        )
        self.assertIn("jazz", keywords)
        self.assertIn("sushi", keywords)
        self.assertIn("jazz", tags)
        self.assertIn("sushi", tags)
        self.assertIn("live music", tags)

    def test_mood_tags_are_seeded(self):
        _keywords, tags = extract_signals("nothing specific planned", "romantic")
        self.assertIn("romantic", tags)
        self.assertIn("wine", tags)

    def test_unknown_mood_adds_no_mood_tags(self):
        _keywords, tags = extract_signals("hiking trip", "party")
        self.assertIn("hiking", tags)
        self.assertNotIn("chill", tags)

    def test_plan_week_shape(self):
        result = plan_week("chill night with jazz and sushi", "chill", "Chicago",
                           MockProvider(), take=4)
        self.assertIn("signals", result)
        self.assertIn("picks", result)
        self.assertEqual(result["signals"]["mood"], "chill")
        self.assertEqual(set(result["picks"].keys()), set(CATEGORIES))
        for cards in result["picks"].values():
            self.assertLessEqual(len(cards), 4)
            for card in cards:
                self.assertTrue(validate_card(card), card)


# ---------------------------------------------------------------- explainer
class TestExplainer(unittest.TestCase):
    def test_why_mentions_a_real_card_tag(self):
        card = {
            "name": "Blue Note Quartet", "category": "music",
            "affinity": 0.94, "popularity": 0.55,
            "tags": ["jazz", "live music", "intimate"],
            "image": None, "source": "mock",
        }
        signals = {"mood": "chill", "tag_names": ["jazz", "chill"], "keywords": ["jazz"]}
        why = explain(card, signals, "chill")
        self.assertIn("jazz", why.lower())
        self.assertIn("94%", why)  # affinity is real data on the card

    def test_no_invented_scores_when_none_present(self):
        card = {
            "name": "Top-rated chain restaurant near you", "category": "dining",
            "affinity": None, "popularity": None,
            "tags": ["popular", "generic"], "image": None, "source": "baseline",
        }
        why = explain(card, {"tag_names": []}, "energetic")
        self.assertNotIn("%", why)
        self.assertIn("energetic", why)

    def test_one_to_two_sentences(self):
        card = {"name": "X", "category": "film", "affinity": None,
                "popularity": None, "tags": ["horror"], "image": None, "source": "mock"}
        why = explain(card, {"tag_names": ["horror"]}, "adventurous")
        sentences = [s for s in why.split(".") if s.strip()]
        self.assertTrue(1 <= len(sentences) <= 2, why)


# ---------------------------------------------------------------- mock provider
class TestMockProvider(unittest.TestCase):
    def test_recommend_shape_and_counts(self):
        p = MockProvider()
        for category in CATEGORIES:
            cards = p.recommend(category, ["jazz", "chill"], "Chicago", take=5)
            self.assertEqual(len(cards), 5)
            for card in cards:
                self.assertTrue(validate_card(card), card)
                self.assertEqual(card["category"], category)
                self.assertEqual(card["source"], "mock")
                self.assertTrue(0.70 <= card["affinity"] <= 0.97)

    def test_recommend_is_deterministic(self):
        p = MockProvider()
        a = p.recommend("music", ["jazz"], "Chicago", take=6)
        b = p.recommend("music", ["jazz"], "Chicago", take=6)
        self.assertEqual(a, b)

    def test_recommend_ranks_tag_overlap_first(self):
        p = MockProvider()
        cards = p.recommend("music", ["jazz"], "Chicago", take=6)
        self.assertEqual(cards[0]["name"], "Blue Note Quartet")

    def test_search_entity_and_tags(self):
        p = MockProvider()
        ents = p.search_entity("ramen")
        self.assertTrue(any("Ramen" in e["name"] for e in ents))
        tags = p.search_tags("jazz")
        self.assertTrue(any(t["name"] == "jazz" for t in tags))


# ---------------------------------------------------------------- qloo provider (no network)
class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestQlooProvider(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"QLOO_API_KEY": "test-key-123"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_raises_when_key_missing(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("QLOO_API_KEY", None)
            with self.assertRaises(QlooNotConfigured):
                QlooProvider()

    def test_recommend_builds_correct_request(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = {k.lower(): v for k, v in req.header_items()}
            captured["timeout"] = timeout
            return _FakeResp({
                "success": True,
                "results": {"entities": [
                    {"name": "Test Artist", "entity_id": "e1",
                     "popularity": 0.8, "affinity": 0.9,
                     "tags": [{"id": "urn:tag:x", "name": "jazz"}],
                     "url": "https://img.example/a.jpg"},
                ]},
            })

        # stub tag resolution so only /v2/insights is exercised
        with mock.patch.object(QlooProvider, "_resolve_tag", return_value=["urn:tag:genre:music:jazz"]), \
             mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            provider = QlooProvider()
            cards = provider.recommend("music", ["jazz"], "Chicago", take=6)

        self.assertIn("hackathon.api.qloo.com", captured["url"])
        self.assertNotIn("api.qloo.com/v2", captured["url"].replace("hackathon.api.qloo.com", ""))
        self.assertIn("filter.type=urn%3Aentity%3Aartist", captured["url"])
        self.assertIn("signal.interests.tags=urn%3Atag%3Agenre%3Amusic%3Ajazz", captured["url"])
        self.assertIn("take=6", captured["url"])
        self.assertEqual(captured["headers"].get("x-api-key"), "test-key-123")
        self.assertNotIn("api_key", captured["url"].lower().split("x-api-key")[0])

        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertTrue(validate_card(card), card)
        self.assertEqual(card["name"], "Test Artist")
        self.assertEqual(card["source"], "qloo")
        self.assertEqual(card["affinity"], 0.9)
        self.assertEqual(card["popularity"], 0.8)
        self.assertEqual(card["tags"], ["jazz"])
        self.assertEqual(card["image"], "https://img.example/a.jpg")

    def test_recommend_place_adds_location_filter(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _FakeResp({"success": True, "results": {"entities": []}})

        with mock.patch.object(QlooProvider, "_resolve_tag", return_value=[]), \
             mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            QlooProvider().recommend("dining", [], "Chicago", take=3)

        self.assertIn("filter.type=urn%3Aentity%3Aplace", captured["url"])
        self.assertIn("filter.location.query=Chicago", captured["url"])

    def test_category_filter_type_map(self):
        self.assertEqual(CATEGORY_FILTER_TYPES["dining"], "urn:entity:place")
        self.assertEqual(CATEGORY_FILTER_TYPES["music"], "urn:entity:artist")
        self.assertEqual(CATEGORY_FILTER_TYPES["film"], "urn:entity:movie")
        self.assertEqual(CATEGORY_FILTER_TYPES["going_out"], "urn:entity:place")

    def test_network_failure_raises_qloo_error(self):
        def boom(req, timeout=None):
            raise urllib.request.URLError("nope")

        with mock.patch.object(urllib.request, "urlopen", side_effect=boom):
            with self.assertRaises(QlooError):
                QlooProvider()._get("/v2/insights", {"filter.type": "urn:entity:artist"})


# ---------------------------------------------------------------- baseline
class TestBaseline(unittest.TestCase):
    def test_baseline_is_honestly_generic(self):
        plan = baseline_plan()
        self.assertEqual(set(plan.keys()), set(CATEGORIES))
        for category, cards in plan.items():
            self.assertEqual(len(cards), 3)
            for card in cards:
                self.assertEqual(card["source"], "baseline")
                self.assertIsNone(card["affinity"])
                self.assertEqual(card["why"], BASELINE_WHY)


# ---------------------------------------------------------------- server
class TestServerImports(unittest.TestCase):
    def test_server_imports_cleanly(self):
        import backend.server  # noqa: F401


if __name__ == "__main__":
    unittest.main()
