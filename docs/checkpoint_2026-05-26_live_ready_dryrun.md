# APIF checkpoint: live-ready dry-run monitoring

Date: 2026-05-26
Repository state: `ed4bb64 Add stop loss monitoring`
GitHub remote: `https://github.com/ojungmin212-dotcom/https-github.com-.git`

## Current goal

Build a user-controlled stock auto trading program for Namu/NH QV OpenAPI.
The user chooses the stock, buy price, sell price, stop-loss price, and quantity.

The current system is ready for real quote monitoring, but real account orders
remain intentionally disabled.

## Current safety state

- `APIF_ENABLE_LIVE_TRADING=NO`
- Trading mode remains `DRY_RUN`
- Real orders are not sent
- Simulated orders are logged under `logs/`
- Emergency stop file: `STOP_TRADING`
- Desktop controller has:
  - DLL check
  - quote lookup
  - one-shot dry monitor
  - continuous dry monitor
  - monitor stop
  - emergency stop / clear emergency stop

## Important local-only files

Do not commit these:

- `.env`
- `native/namu_bridge/bin/`
- `native/namu_bridge/obj/`
- `logs/`

The local `.env` currently points to the native 32-bit bridge:

```text
APIF_NAMU_QV_PATH=C:\Users\Win\Desktop\openapi.nm
APIF_NAMU_BRIDGE_COMMAND=C:\Users\Win\Documents\Codex\2026-05-26\apif\native\namu_bridge\bin\Win32\Release\namu_bridge.exe
APIF_ENABLE_LIVE_TRADING=NO
```

User credentials must be typed into the desktop controller only. Do not ask the
user to paste passwords into chat.

## Architecture

- `apif_bot/desktop_app.py`
  Desktop controller UI.

- `apif_bot/engine.py`
  Trading state machine:
  wait to buy, hold, sell target, stop-loss, finish.

- `apif_bot/models.py`
  Trading plan and `stop_loss_price`.

- `apif_bot/safety.py`
  Allowed symbol, max order amount, max quantity, market hours, emergency stop.

- `apif_bot/bridge.py`
  JSON-line bridge client.

- `native/namu_bridge/src/namu_bridge.cpp`
  32-bit native bridge for `wmca.dll`.
  Quote lookup works through `IVWUTKMST04.UNT`.
  Order handling is still disabled.

- `config/trade_plan.live_ready.json`
  Live-ready dry-run config with market-hours and stop-loss.

## Verified

Tests:

```powershell
python -m unittest discover -s tests
```

Current result:

```text
Ran 13 tests ... OK
```

Native bridge:

- Built as x86
- `wmca.dll` ping succeeded
- Real quote lookup succeeded earlier for `005930`

## How to resume

1. Open the controller:

```powershell
powershell -ExecutionPolicy Bypass -File tools\open_controller.ps1
```

2. User enters credentials inside the controller only.
3. Click `DLL 확인`.
4. Click `현재가 조회`.
5. Set:
   - 종목코드
   - 매수가
   - 손절가
   - 매도가
   - 수량
6. Click `감시 시작`.
7. Review `logs/desktop_orders.csv` after a dry-run event.

## Next development tasks

After several days of dry-run monitoring:

1. Review missed quotes, freezes, login failures, and UI usability.
2. Add persistent settings for non-secret values.
3. Add order history viewer inside the desktop controller.
4. Add better Korean labels for engine messages.
5. Only after mock/dry-run confidence, design the real-order path.
6. Real-order path must require an explicit extra confirmation and small limits.

## Absolute rule

Do not enable real account orders casually. Keep live trading disabled until the
user explicitly asks for it after dry-run review, and keep a separate safety
confirmation step.
