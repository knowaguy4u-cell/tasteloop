"""Vercel serverless function: GET /api/health.

Thin adapter over backend.server — same payload as the stdlib server's
/api/health route. QLOO_API_KEY is read from the environment (Vercel env var).
"""

import os
import sys
from http.server import BaseHTTPRequestHandler

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)  # repo root: tasteloop/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.server import _configured, _json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _json(self, 200, {
            "ok": True,
            "mode": "live" if _configured() else "mock",
            "qloo_configured": _configured(),
        })
