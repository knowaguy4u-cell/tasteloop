"""QlooProvider: live Taste API provider for the hackathon endpoint.

Facts coded against (verified from official docs 2026-10-01):
- Hackathon base URL: https://hackathon.api.qloo.com (hackathon keys 401 elsewhere)
- Auth: X-Api-Key request header (never query param, never Bearer)
- Primary endpoint: GET /v2/insights with filter.type (required). Supported
  filter.type values: urn:entity:artist, urn:entity:book, urn:entity:brand,
  urn:entity:destination, urn:entity:movie, urn:entity:person, urn:entity:place,
  urn:entity:podcast, urn:entity:tv_show, urn:entity:video_game
  (/recommendations and /recs are legacy and unsupported — never called)
- Signals: signal.interests.tags=<comma-separated tag URNs>,
  signal.interests.entities=<entity IDs>, take=<1-50>.
  Invalid params are silently ignored — only documented params are used.
- Tag lookup: GET /v2/tags (keyword -> tag URNs like urn:tag:genre:media:action)
- Entity lookup: GET /search?query=...&take=...
- Insights envelope: {success, results:{entities:[...]}} (also accepts data["entities"])

No API key is required to import or construct the module — but constructing
QlooProvider raises QlooNotConfigured when QLOO_API_KEY is absent, so the
server can cleanly fall back to MockProvider. Every network call uses urllib
from the stdlib; nothing here touches the network at import time.
"""

import json
import os
import urllib.parse
import urllib.request

BASE_URL = "https://hackathon.api.qloo.com"
API_KEY_ENV = "QLOO_API_KEY"
REQUEST_TIMEOUT = 15

CATEGORY_FILTER_TYPES = {
    "dining": "urn:entity:place",
    "music": "urn:entity:artist",
    "film": "urn:entity:movie",
    "going_out": "urn:entity:place",
}


class QlooNotConfigured(Exception):
    """Raised when QLOO_API_KEY is not set in the environment."""


class QlooError(Exception):
    """Raised when the Qloo API returns an error or unusable response."""


def _as_float(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if 0.0 <= v <= 1.0 else None


class QlooProvider:
    def __init__(self, api_key=None):
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        if not key:
            raise QlooNotConfigured(
                "QLOO_API_KEY is not set; QlooProvider cannot be used."
            )
        self.api_key = key
        self._tag_cache = {}  # tag-name (lowercased) -> list of URNs

    # ---- low-level HTTP ----

    def _get(self, path, params):
        query = urllib.parse.urlencode(params)
        url = BASE_URL + path + ("?" + query if query else "")
        req = urllib.request.Request(url, headers={"X-Api-Key": self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                payload = resp.read()
        except Exception as exc:  # URLError, HTTPError, timeouts, ...
            raise QlooError("Qloo request failed: %s %s" % (type(exc).__name__, exc))
        try:
            return json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise QlooError("Qloo returned non-JSON: %s" % exc)

    # ---- tag resolution ----

    @staticmethod
    def _extract_tag_urns(data):
        """Pull (urn, name) pairs out of a /v2/tags response, defensively."""
        if isinstance(data, dict):
            for key in ("results", "tags", "data"):
                node = data.get(key)
                if isinstance(node, list):
                    items = node
                    break
                if isinstance(node, dict) and isinstance(node.get("tags"), list):
                    items = node["tags"]
                    break
            else:
                items = []
        elif isinstance(data, list):
            items = data
        else:
            items = []
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            urn = item.get("id") or item.get("urn") or item.get("tag_id")
            name = item.get("name")
            if urn and name:
                out.append((str(urn), str(name)))
        return out

    def _resolve_tag(self, tag_name):
        """Resolve one tag name to a list of tag URNs (cached in-memory)."""
        key = tag_name.strip().lower()
        if not key:
            return []
        if key in self._tag_cache:
            return self._tag_cache[key]
        data = self._get("/v2/tags", {"query": tag_name, "take": 5})
        urns = [urn for urn, _name in self._extract_tag_urns(data)]
        self._tag_cache[key] = urns
        return urns

    # ---- interface ----

    def recommend(self, category, tag_names, location, take=6):
        if category not in CATEGORY_FILTER_TYPES:
            raise ValueError("unknown category: %r" % (category,))
        filter_type = CATEGORY_FILTER_TYPES[category]
        take = max(1, min(int(take or 6), 50))

        urns = []
        for name in tag_names or []:
            urns.extend(self._resolve_tag(name))
        # de-dupe, preserve order
        seen = set()
        urns = [u for u in urns if not (u in seen or seen.add(u))]

        params = {"filter.type": filter_type, "take": take}
        if urns:
            params["signal.interests.tags"] = ",".join(urns)
        if filter_type == "urn:entity:place" and location:
            # harmless if the API ignores it
            params["filter.location.query"] = location

        data = self._get("/v2/insights", params)
        entities = self._extract_entities(data)
        return [self._to_card(e, category) for e in entities[:take]]

    def search_entity(self, query, etype=None):
        params = {"query": query or "", "take": 10}
        if etype and etype in CATEGORY_FILTER_TYPES:
            params["filter.type"] = CATEGORY_FILTER_TYPES[etype]
        data = self._get("/search", params)
        return [self._to_card(e, etype or "dining") for e in self._extract_entities(data)]

    def search_tags(self, query, take=10):
        data = self._get("/v2/tags", {"query": query or "", "take": max(1, int(take or 10))})
        return [{"id": urn, "name": name} for urn, name in self._extract_tag_urns(data)]

    # ---- normalization ----

    @staticmethod
    def _extract_entities(data):
        """Accept {success, results:{entities:[...]}} and data["entities"] shapes."""
        if not isinstance(data, dict):
            return []
        for node in (data.get("results"), data.get("data")):
            if isinstance(node, dict) and isinstance(node.get("entities"), list):
                return [e for e in node["entities"] if isinstance(e, dict)]
        if isinstance(data.get("entities"), list):
            return [e for e in data["entities"] if isinstance(e, dict)]
        return []

    @staticmethod
    def _to_card(entity, category):
        tags = []
        for t in entity.get("tags") or []:
            if isinstance(t, dict) and t.get("name"):
                tags.append(str(t["name"]))
            elif isinstance(t, str):
                tags.append(t)
        return {
            "name": str(entity.get("name") or "Unknown"),
            "category": category,
            "affinity": _as_float(entity.get("affinity")),
            "popularity": _as_float(entity.get("popularity")),
            "tags": tags,
            "image": entity.get("url") if isinstance(entity.get("url"), str) else None,
            "source": "qloo",
        }
