# Namu bridge protocol

The real Namu OpenAPI helper must be a 32-bit process because `wmca.dll` is x86.
The main Python trading engine talks to that helper through JSON lines.

The helper reads one JSON object from standard input and writes one JSON object
to standard output.

## Ping

Request:

```json
{"command": "ping"}
```

Response:

```json
{"ok": true, "data": {"status": "ready"}}
```

## Quote

Request:

```json
{"command": "quote", "symbol": "005930"}
```

Response:

```json
{"ok": true, "data": {"symbol": "005930", "price": 70000}}
```

The real helper should call `wmcaQuery()` with `IVWUTKMST04.UNT`, `KRX`, or `NXT`
and return `stck_prpr` as the integer price.

## Order

Request:

```json
{
  "command": "order",
  "symbol": "005930",
  "side": "BUY",
  "price": 70000,
  "quantity": 1
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "accepted": true,
    "order_id": "1234567890",
    "message": "accepted"
  }
}
```

The real helper should call `wmcaQuery()` with `c8102` only after mock trading
has been verified.

## Local mock helper

During development, the Python mock helper can be used:

```powershell
python -m apif_bot.cli --quote-source namu --max-ticks 1 --config config/trade_plan.example.json
```

Set this in the local `.env` file:

```text
APIF_NAMU_BRIDGE_COMMAND=python apif_bot/mock_bridge.py
```
