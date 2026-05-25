from __future__ import annotations

import json
import sys
import uuid


def main() -> None:
    raw = sys.stdin.readline()
    if not raw.strip():
        _send({"ok": False, "error": "No request received."})
        return
    request = json.loads(raw)
    command = request.get("command")

    if command == "ping":
        _send({"ok": True, "data": {"status": "ready"}})
    elif command == "quote":
        _send({"ok": True, "data": {"symbol": request["symbol"], "price": 70000}})
    elif command == "order":
        _send(
            {
                "ok": True,
                "data": {
                    "accepted": True,
                    "order_id": f"MOCK-{uuid.uuid4().hex[:10].upper()}",
                    "message": "Mock bridge order accepted.",
                },
            }
        )
    else:
        _send({"ok": False, "error": f"Unknown command: {command}"})


def _send(payload: dict) -> None:
    print(json.dumps(payload), flush=True)


if __name__ == "__main__":
    main()
