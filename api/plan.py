"""Vercel serverless function: POST /api/plan.

Thin adapter over backend.server — same request/response contract as the
stdlib server's /api/plan route. A Qloo failure never 500s: falls back to
mock picks with a "warning" field.
"""

import datetime
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)  # repo root: tasteloop/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.baseline import baseline_plan  # noqa: E402
from backend.providers.mock import MockProvider  # noqa: E402
from backend.server import _build_plan, _choose_provider, _json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            _json(self, 400, {"success": False, "error": "invalid JSON body"})
            return
        if not isinstance(payload, dict):
            _json(self, 400, {"success": False, "error": "JSON body must be an object"})
            return

        week_text = payload.get("week_text") or ""
        mood = payload.get("mood") or ""
        city = payload.get("city") or ""

        provider, mode = _choose_provider()
        warning = None
        try:
            signals, plan = _build_plan(provider, week_text, mood, city)
        except Exception as exc:
            if mode == "live":
                warning = "Qloo request failed (%s); served mock picks instead." % exc
                provider, mode = MockProvider(), "mock"
                signals, plan = _build_plan(provider, week_text, mood, city)
            else:
                _json(self, 500, {"success": False, "error": "planner failed: %s" % exc})
                return

        response = {
            "success": True,
            "mode": mode,
            "signals": signals,
            "plan": plan,
            "baseline": baseline_plan(),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if warning:
            response["warning"] = warning
        _json(self, 200, response)
