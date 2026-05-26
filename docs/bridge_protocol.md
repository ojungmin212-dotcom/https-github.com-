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

The native helper draft lives in `native/namu_bridge`. It is intentionally scoped
to quote lookup first.

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

The real helper should call `wmcaQuery()` with the correct buy/sell TR only
after mock trading has been verified.

Current native helper behavior is intentionally blocked. It accepts the order
request shape, resolves the correct TR, checks whether required order password
environment values are present, and returns `accepted: false` with a block
message. It does not transmit an order to Namu.

Local Namu order documents in `C:\Users\Win\Desktop\openapi.nm` show these
stock-order TR mappings:

- `c8101`: stock sell order
- `c8102`: stock buy order

Both order types require the account password hash and separate order/trading
password hashes. The controller therefore keeps live order transmission blocked
until those password fields, order confirmation, duplicate-order prevention,
and fill confirmation are implemented.

## Local mock helper

During development, the Python mock helper can be used:

```powershell
python -m apif_bot.cli --quote-source namu --max-ticks 1 --config config/trade_plan.example.json
```

Set this in the local `.env` file:

```text
APIF_NAMU_BRIDGE_COMMAND=python apif_bot/mock_bridge.py
```
