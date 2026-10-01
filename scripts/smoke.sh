#!/usr/bin/env bash
# TasteLoop backend smoke test: start server, hit /api/health and /api/plan,
# assert JSON keys, shut down. Exits nonzero on any failure.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT=8123
export PORT

echo "== starting server on :$PORT =="
python3 -m backend.server > /tmp/tasteloop-smoke.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# wait for the port to answer (max ~10s)
for i in $(seq 1 50); do
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/api/health"; then
    break
  fi
  sleep 0.2
  if [ "$i" -eq 50 ]; then
    echo "FAIL: server never answered /api/health"; cat /tmp/tasteloop-smoke.log; exit 1
  fi
done

echo "== GET /api/health =="
curl -sf "http://127.0.0.1:$PORT/api/health" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["ok"] is True, d
assert d["mode"] == "mock", d            # no QLOO_API_KEY in smoke env
assert d["qloo_configured"] is False, d
print("health OK:", d)
'

echo "== POST /api/plan =="
curl -sf -X POST "http://127.0.0.1:$PORT/api/plan" \
  -H 'Content-Type: application/json' \
  -d '{"week_text":"chill Friday night: jazz club, then sushi with friends","mood":"chill","city":"Chicago"}' \
| python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["success"] is True, d
assert d["mode"] == "mock", d
assert "warning" not in d, d
sig = d["signals"]
assert sig["mood"] == "chill", sig
assert "jazz" in sig["tag_names"], sig
assert "sushi" in sig["tag_names"], sig
plan = d["plan"]
assert set(plan.keys()) == {"dining", "music", "film", "going_out"}, plan.keys()
for cat, cards in plan.items():
    assert 1 <= len(cards) <= 6, (cat, len(cards))
    for c in cards:
        for k in ("name", "category", "affinity", "popularity", "tags", "image", "source", "why"):
            assert k in c, (cat, k, c)
        assert c["why"] and isinstance(c["why"], str), c
        assert c["source"] == "mock", c
base = d["baseline"]
assert set(base.keys()) == {"dining", "music", "film", "going_out"}
for cat, cards in base.items():
    assert len(cards) == 3, (cat, len(cards))
    for c in cards:
        assert c["source"] == "baseline" and c["affinity"] is None, c
        assert "not matched to your taste signals" in c["why"], c
assert d["generated_at"], d
print("plan OK: mode=%s signals=%s" % (d["mode"], sig["tag_names"][:6]))
'

echo "== SMOKE PASSED =="
