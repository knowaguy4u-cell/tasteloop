"""TasteLoop Agent backend server (stdlib http.server only).

Routes:
    GET  /            -> ../frontend/index.html
    GET  /static/*    -> ../frontend/<path>   (path-traversal guarded)
    GET  /api/health  -> {"ok": true, "mode": "live"|"mock", "qloo_configured": bool}
    POST /api/plan    -> {"success", "mode", "signals", "plan", "baseline",
                          "generated_at", ["warning"]}

Provider selection: QlooProvider when QLOO_API_KEY is set, else MockProvider.
A Qloo failure never 500s — the server falls back to mock and includes a
"warning" field. Same-origin only; no CORS headers needed. Port: $PORT or 8000.
"""

import datetime
import json
import mimetypes
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)  # tasteloop/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.baseline import baseline_plan  # noqa: E402
from backend.explainer import explain  # noqa: E402
from backend.planner import plan_week  # noqa: E402
from backend.providers.mock import MockProvider  # noqa: E402
from backend.providers.qloo import QlooNotConfigured, QlooProvider  # noqa: E402

FRONTEND_DIR = os.path.join(_ROOT, "frontend")


def _configured():
    return bool(os.environ.get("QLOO_API_KEY"))


def _choose_provider():
    """Return (provider, mode). Never raises for a missing key."""
    if _configured():
        try:
            return QlooProvider(), "live"
        except QlooNotConfigured:
            pass
    return MockProvider(), "mock"


def _build_plan(provider, week_text, mood, city):
    result = plan_week(week_text, mood, city, provider, take=6)
    signals = result["signals"]
    plan = {}
    for category, cards in result["picks"].items():
        enriched = []
        for card in cards:
            card = dict(card)
            card["why"] = explain(card, signals, signals.get("mood") or mood)
            enriched.append(card)
        plan[category] = enriched
    return signals, plan


def _json(handler, status, obj):
    body = json.dumps(obj).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "TasteLoop/1.0"

    def log_message(self, fmt, *args):  # keep logs quiet-ish
        sys.stderr.write("tasteloop: " + fmt % args + "\n")

    # ---- GET ----
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            _json(self, 200, {
                "ok": True,
                "mode": "live" if _configured() else "mock",
                "qloo_configured": _configured(),
            })
            return

        if path == "/" or path == "/index.html":
            self._serve_file("index.html")
            return

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_file(rel)
            return

        _json(self, 404, {"success": False, "error": "not found"})

    def _serve_file(self, rel):
        safe = os.path.normpath(rel)
        if safe.startswith("..") or os.path.isabs(safe):
            _json(self, 403, {"success": False, "error": "forbidden"})
            return
        full = os.path.join(FRONTEND_DIR, safe)
        if not os.path.isfile(full):
            _json(self, 404, {"success": False, "error": "frontend file not found: " + safe})
            return
        ctype, _ = mimetypes.guess_type(full)
        with open(full, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- POST ----
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/plan":
            _json(self, 404, {"success": False, "error": "not found"})
            return

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
                # Never 500 on a provider failure: fall back to mock.
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


def main():
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("TasteLoop backend on :%d (mode=%s)" % (port, "live" if _configured() else "mock"),
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
